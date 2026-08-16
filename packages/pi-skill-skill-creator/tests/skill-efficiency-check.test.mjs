import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const skillDir = path.resolve(import.meta.dirname, "..", "skills", "skill-creator");
const checker = path.join(skillDir, "scripts", "skill-efficiency-check.py");
const piProfile = path.join(skillDir, "assets", "host-profiles", "pi.json");

function run(args, cwd) {
	const result = spawnSync("python", [checker, ...args], {
		cwd: cwd ?? root,
		encoding: "utf8",
		timeout: 60000,
	});
	return {
		status: result.status,
		stdout: (result.stdout ?? "").replace(/\r\n/g, "\n"),
		stderr: (result.stderr ?? "").replace(/\r\n/g, "\n"),
	};
}

function tempSkill() {
	return fs.mkdtempSync(path.join(os.tmpdir(), "skill-check-test-"));
}

function write(file, content) {
	const target = path.join(root, file);
	fs.mkdirSync(path.dirname(target), { recursive: true });
	fs.writeFileSync(target, content);
	return target;
}

let root = tempSkill();
const results = [];
function test(name, fn) {
	try {
		root = tempSkill();
		fn();
		results.push(`- ${name}: passed`);
	} catch (error) {
		results.push(`- ${name}: FAILED\n  ${error.message}`);
		process.exitCode = 1;
	} finally {
		fs.rmSync(root, { recursive: true, force: true });
	}
}

const validFrontmatter = ['---', 'name: demo-skill', 'description: "Demo. Use for x."', '---', '', "# Demo", ""].join("\n");

test("valid direct and indirect graph passes strict", () => {
	write("SKILL.md", `${validFrontmatter}\nSee [guide](references/guide.md) and run scripts/check.py.\n`);
	write("references/guide.md", "# Guide\n\nTemplate: [tpl](../assets/template.md)\n");
	write("assets/template.md", "tpl\n");
	write("scripts/check.py", "print(1)\n");
	const result = run([".", "--strict"]);
	assert.equal(result.status, 0, result.stdout);
	assert.match(result.stdout, /## Issues\n- none/);
	assert.match(result.stdout, /graph_edges: 3/);
});

test("missing target fails with file and line", () => {
	write("SKILL.md", `${validFrontmatter}\n[guide](references/missing.md)\n`);
	const result = run(["."]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /SKILL\.md:8: dangling reference: references\/missing\.md resolves to missing references\/missing\.md/);
});

test("nested relative link resolves against containing file", () => {
	write("SKILL.md", `${validFrontmatter}\n[guide](references/guide.md)\n`);
	write("references/guide.md", "# Guide\n\n[tpl](../assets/template.md)\n");
	write("assets/template.md", "tpl\n");
	const result = run([".", "--strict"]);
	assert.equal(result.status, 0, result.stdout);
});

test("fragment-only link is ignored", () => {
	write("SKILL.md", `${validFrontmatter}\nJump [top](#top).\n`);
	const result = run(["."]);
	assert.equal(result.status, 0, result.stdout);
});

test("external url recorded, not fetched, no diagnostic", () => {
	write("SKILL.md", `${validFrontmatter}\n[docs](https://example.com/docs) fragment [a](#a)\n`);
	const result = run(["."]);
	assert.equal(result.status, 0, result.stdout);
	assert.match(result.stdout, /external_links: 1/);
});

test("link inside fenced code is not extracted", () => {
	write("SKILL.md", `${validFrontmatter}\nExample text:\n\n\`\`\`text\n[ghost](references/ghost.md)\n\`\`\`\n`);
	const result = run(["."]);
	assert.equal(result.status, 0, result.stdout);
});

test("path escape fails", () => {
	write("SKILL.md", `${validFrontmatter}\n[outside](../outside.md) and [abs](/etc/passwd)\n`);
	const result = run(["."]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /path escapes the skill root: \.\.\/outside\.md/);
	assert.match(result.stdout, /absolute path escapes the skill root: \/etc\/passwd/);
});

test("case mismatch fails on windows", () => {
	write("SKILL.md", `${validFrontmatter}\n[guide](references/Guide.md)\n`);
	write("references/guide.md", "# Guide\n");
	const result = run(["."]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /case mismatch: references\/Guide\.md should be references\/guide\.md/);
});

test("cycle is reported with the complete path", () => {
	write("SKILL.md", `${validFrontmatter}\n[a](references/a.md)\n`);
	write("references/a.md", "# A\n\n[b](b.md)\n");
	write("references/b.md", "# B\n\n[home](../SKILL.md)\n");
	const result = run(["."]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /reference cycle: SKILL\.md -> references\/a\.md -> references\/b\.md -> SKILL\.md/);
});

test("orphan warns normally and fails strict", () => {
	write("SKILL.md", `${validFrontmatter}\nno links here\n`);
	write("assets/orphan.md", "# Orphan\n");
	const normal = run(["."]);
	assert.equal(normal.status, 0, normal.stdout);
	assert.match(normal.stdout, /orphaned supporting file: assets\/orphan\.md/);
	const strict = run([".", "--strict"]);
	assert.equal(strict.status, 1);
});

test("backslash separators in mentions resolve", () => {
	write("SKILL.md", `${validFrontmatter}\nRun scripts\\check.py when needed.\n`);
	write("scripts/check.py", "print(1)\n");
	const result = run([".", "--strict"]);
	assert.equal(result.status, 0, result.stdout);
});

test("adjacent-directory idiom is not a link", () => {
	write("SKILL.md", `${validFrontmatter}\nRunbooks may lack references/scripts entirely; use assets only if needed.\n`);
	const result = run([".", "--strict"]);
	assert.equal(result.status, 0, result.stdout);
});

test("malformed profile fails with clear error", () => {
	const badProfile = path.join(root, "bad.json");
	fs.writeFileSync(badProfile, JSON.stringify({ schema_version: 1, profile: "x", profile_description: "d", frontmatter: { required: ["name"], allowed: ["name"] }, name: { pattern: "^a$", max_length: 5 }, description: { max_length: 10, warn_above: 5 }, supporting_directories: ["references"], ignored_paths: [], checks: { forbidden_headings: true, unknown_fields: "suggest" }, extra_key: true }));
	const result = run([".", "--profile", badProfile]);
	assert.equal(result.status, 1, `${result.stdout}\n${result.stderr}`);
	assert.match(result.stdout, /host profile is invalid: unknown profile key\(s\) in host profile bad\.json: extra_key/);
});

test("profile rejects missing required key", () => {
	const badProfile = path.join(root, "no-description-object.json");
	fs.writeFileSync(badProfile, JSON.stringify({ schema_version: 1, profile: "x", profile_description: "d", frontmatter: { required: ["name"], allowed: ["name"] }, name: { pattern: "^a$", max_length: 5 }, supporting_directories: ["references"], ignored_paths: [], checks: { forbidden_headings: true, unknown_fields: "suggest" } }));
	const result = run([".", "--profile", badProfile]);
	assert.equal(result.status, 1);
	assert.match(result.stdout, /host profile is invalid/);
});

test("generic host profile validates the bundled skill", () => {
	const result = run([skillDir, "--host", "generic"]);
	assert.equal(result.status, 0, result.stdout);
	assert.match(result.stdout, /profile: generic/);
});

test("legacy invocation shape stays compatible", () => {
	const result = run([skillDir]);
	assert.equal(result.status, 0, result.stdout);
	assert.match(result.stdout, /# Skill Efficiency Check/);
	assert.match(result.stdout, /## Issues\n- none/);
	assert.match(result.stdout, /## Warnings\n- none/);
	assert.match(result.stdout, /## Suggestions\n- none/);
});

test("json output contains stable graph fields", () => {
	const result = run([skillDir, "--format", "json"]);
	assert.equal(result.status, 0, result.stdout);
	const report = JSON.parse(result.stdout);
	for (const key of ["profile", "strict", "summary", "nodes", "edges", "external_links", "issues", "warnings", "suggestions"]) {
		assert.ok(key in report, `missing key ${key}`);
	}
	assert.ok(report.nodes.some((node) => node.path === "SKILL.md" && node.kind === "root"));
	assert.ok(report.nodes.some((node) => node.path === "references/skills-reference-guide-for-agents.md" && node.kind === "reference"));
	assert.ok(report.nodes.some((node) => node.path === "assets/host-profiles/pi.json" && node.kind === "asset"));
	assert.ok(report.nodes.some((node) => node.path === "evals/cases.json" && node.kind === "eval"));
});

test("bundled skill passes strict self-validation", () => {
	const result = run([skillDir, "--host", "pi", "--strict"]);
	assert.equal(result.status, 0, result.stdout);
	assert.match(result.stdout, /## Issues\n- none/);
	assert.match(result.stdout, /## Warnings\n- none/);
});

test("pi profile matches shipped json", () => {
	const data = JSON.parse(fs.readFileSync(piProfile, "utf8"));
	assert.equal(data.profile, "pi");
	assert.equal(data.description.max_length, 1024);
	assert.equal(data.name.max_length, 64);
	assert.deepEqual(data.frontmatter.allowed, ["name", "description", "license", "compatibility", "metadata", "allowed-tools", "disable-model-invocation"]);
	assert.ok(data.supporting_directories.includes("evals"));
});

console.log("# skill-efficiency-check tests\n");
console.log(results.join("\n"));
console.log(`\n${process.exitCode ? "FAILED" : "all passed"}`);
