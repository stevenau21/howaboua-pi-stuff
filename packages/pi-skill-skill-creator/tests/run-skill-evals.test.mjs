import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const skillDir = path.resolve(import.meta.dirname, "..", "skills", "skill-creator");
const runner = path.join(skillDir, "scripts", "run-skill-evals.py");

function runEval(args, cwd = skillDir) {
	const result = spawnSync("python", [runner, ...args], { cwd, encoding: "utf8", timeout: 60000 });
	return { status: result.status, stdout: result.stdout, stderr: result.stderr };
}

function normalize(text) {
	return (text ?? "").replace(/\r\n/g, "\n");
}

function writeAdapter(name, body) {
	const file = path.join(root, name);
	fs.writeFileSync(file, body);
	return `node ${JSON.stringify(file)}`;
}

let root;
const results = [];
function test(name, fn) {
	try {
		root = fs.mkdtempSync(path.join(os.tmpdir(), "skill-evals-test-"));
		fn();
		results.push(`- ${name}: passed`);
	} catch (error) {
		results.push(`- ${name}: FAILED\n  ${error.message}`);
		process.exitCode = 1;
	} finally {
		fs.rmSync(root, { recursive: true, force: true });
	}
}

test("bundled fixtures validate offline", () => {
	const result = runEval([]);
	assert.equal(result.status, 0, result.stdout);
	assert.match(result.stdout, /total: 18\s+passed: 18\s+failed: 0/);
});

test("bundled fixtures validate in json mode", () => {
	const result = runEval(["--format", "json"]);
	assert.equal(result.status, 0, result.stdout);
	const report = JSON.parse(result.stdout);
	assert.equal(report.summary.failed, 0);
	assert.ok(report.results.every((entry) => entry.status === "fixture-valid"));
});

test("duplicate case id fails", () => {
	const cases = path.join(root, "cases.json");
	const one = { id: "dup", kind: "trigger", request: "r", expect: { activated: true } };
	fs.writeFileSync(cases, JSON.stringify({ schema_version: 1, cases: [one, { ...one }] }));
	const result = runEval(["--cases", cases]);
	assert.equal(result.status, 2);
	assert.match(result.stderr, /duplicate case id: dup/);
});

test("invalid expect key fails with valid keys listed", () => {
	const cases = path.join(root, "cases.json");
	fs.writeFileSync(cases, JSON.stringify({ schema_version: 1, cases: [{ id: "bad", kind: "trigger", request: "r", expect: { activated: true, bogus: 1 } }] }));
	const result = runEval(["--cases", cases]);
	assert.equal(result.status, 2);
	assert.match(result.stderr, /unknown expect key\(s\): bogus/);
	assert.match(result.stderr, /valid keys: activated/);
});

test("invalid diagnostics regex fails", () => {
	const cases = path.join(root, "cases.json");
	fs.writeFileSync(cases, JSON.stringify({ schema_version: 1, cases: [{ id: "bad-regex", kind: "trigger", request: "r", expect: { activated: true, diagnostics_present: ["[unclosed"] } }] }));
	const result = runEval(["--cases", cases]);
	assert.equal(result.status, 2);
	assert.match(result.stderr, /not a valid regex/);
});

test("adapter success and non-trigger match structurally", () => {
	const adapter = writeAdapter(
		"ok.mjs",
		[
			'import { readFileSync } from "node:fs";',
			"const c = JSON.parse(readFileSync(0, \"utf8\"));",
			"function sample(re) {",
			'			if (re.includes(".pi") || re.includes("/skills/")) return ".pi/skills/<name>";',
			'			if (re.startsWith("--")) return "--skill path";',
			'			if (re === "Global|Project-local|Custom") return "Global, Project-local, or Custom";',
			'			if (re === "release-tagging") return "release-tagging";',
			'			if (re === "existing") return "existing";',
			'			if (re === "strict") return "strict";',
			'			if (re === "profile") return "profile";',
			'			return re.split("|")[0].replace(/\\./g, "");',
			"}",
			"const out = {",
			"	id: c.id,",
			"	activated: c.expect.activated,",
			"	artifacts: c.expect.artifacts_present ?? [],",
			"	diagnostics: (c.expect.diagnostics_present ?? []).map(sample),",
			"	actions: [],",
			"};",
			'console.log(JSON.stringify(out));',
		].join("\n"),
	);
	const result = runEval(["--adapter", adapter]);
	assert.equal(result.status, 0, result.stdout);
	assert.match(result.stdout, /failed: 0/);
});

test("adapter mismatch fails the case", () => {
	const adapter = writeAdapter("wrong.mjs", [
		'import { readFileSync } from "node:fs";',
		"const c = JSON.parse(readFileSync(0, \"utf8\"));",
		'console.log(JSON.stringify({ id: c.id, activated: !c.expect.activated }));',
	].join("\n"));
	const result = runEval(["--adapter", adapter]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /expected activated=/);
});

test("malformed adapter output fails", () => {
	const adapter = writeAdapter("garbage.mjs", 'import { readFileSync } from "node:fs"; readFileSync(0, "utf8"); console.log("{{{");');
	const result = runEval(["--adapter", adapter]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /adapter output is not valid JSON/);
});

test("adapter timeout fails", () => {
	const adapter = writeAdapter(
		"slow.mjs",
		[
			'import { readFileSync } from "node:fs";',
			'import { setTimeout as sleep } from "node:timers/promises";',
			"readFileSync(0, \"utf8\");",
			"await sleep(60000);",
		].join("\n"),
	);
	const result = runEval(["--adapter", adapter, "--timeout", "1"], skillDir);
	assert.equal(result.status, 1);
	assert.match(normalize(result.stdout), /adapter timed out after 1s/);
});

test("nonzero adapter exit fails", () => {
	const adapter = writeAdapter("crash.mjs", 'import { readFileSync } from "node:fs"; readFileSync(0, "utf8"); process.exit(3);');
	const result = runEval(["--adapter", adapter]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /adapter exited with code 3/);
});

test("wrong observation id fails", () => {
	const adapter = writeAdapter("wrongid.mjs", 'import { readFileSync } from "node:fs"; readFileSync(0, "utf8"); console.log(JSON.stringify({ id: "other", activated: true }));');
	const result = runEval(["--adapter", adapter]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /adapter returned id 'other'; expected/);
});

test("secrets are redacted in reports", () => {
	const cases = path.join(root, "cases.json");
	fs.writeFileSync(
		cases,
		JSON.stringify({
			schema_version: 1,
			cases: [
				{
					id: "secret-check",
					kind: "trigger",
					request: "r",
					expect: { activated: true, diagnostics_present: ["nomatch-xyz"] },
				},
			],
		}),
	);
	const adapter = writeAdapter(
		"secret.mjs",
		[
			'import { readFileSync } from "node:fs";',
			"const c = JSON.parse(readFileSync(0, \"utf8\"));",
			'console.log(JSON.stringify({ id: c.id, activated: true, diagnostics: ["token sk-abcdefgh12345678 leaked"] }));',
		].join("\n"),
	);
	const result = runEval(["--cases", cases, "--adapter", adapter]);
	const out = normalize(result.stdout);
	assert.equal(result.status, 1);
	assert.doesNotMatch(out, /sk-abcdefgh12345678/);
	assert.match(out, /\[REDACTED\]/);
});

console.log("# run-skill-evals tests\n");
console.log(results.join("\n"));
console.log(`\n${process.exitCode ? "FAILED" : "all passed"}`);
