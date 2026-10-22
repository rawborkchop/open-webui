import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
test('artifact verification works in paths with spaces and detects modified artifact bytes', () => {
	// Arrange
	const root = mkdtempSync(join(tmpdir(), 'openwebui artifact test '));
	const verifier = join(root, 'scripts/encryption/artifact.mjs');
	const artifact = join(root, 'src/lib/encryption/vendor/pkg');
	const metadata = join(root, 'metadata.json');
	mkdirSync(dirname(verifier), { recursive: true });
	mkdirSync(join(root, 'crypto/encryption/src'), { recursive: true });
	mkdirSync(artifact, { recursive: true });
	writeFileSync(verifier, readFileSync(fileURLToPath(new URL('./artifact.mjs', import.meta.url))));
	writeFileSync(join(root, 'scripts/encryption/build.py'), 'build');
	writeFileSync(join(root, 'crypto/encryption/src/lib.rs'), 'source\r\n');
	writeFileSync(join(artifact, 'module.wasm'), 'reviewed bytes');
	writeFileSync(metadata, '{"packages":[]}');
	try {
		// Act
		const generated = spawnSync(process.execPath, [verifier, '--write', '--metadata', metadata], { encoding: 'utf8' });
		writeFileSync(join(root, 'crypto/encryption/src/lib.rs'), 'source\n');
		const verified = spawnSync(process.execPath, [verifier], { encoding: 'utf8' });
		writeFileSync(join(artifact, 'module.wasm'), 'modified bytes');
		const modified = spawnSync(process.execPath, [verifier], { encoding: 'utf8' });
		writeFileSync(join(artifact, 'module.wasm'), 'reviewed bytes');
		writeFileSync(join(root, 'crypto/encryption/src/lib.rs'), 'changed source\n');
		const changedSource = spawnSync(process.execPath, [verifier], { encoding: 'utf8' });
		// Assert
		assert.equal(generated.status, 0, generated.stderr);
		assert.equal(verified.status, 0, verified.stderr);
		assert.notEqual(modified.status, 0);
		assert.match(modified.stderr, /checksum mismatch/);
		assert.notEqual(changedSource.status, 0);
		assert.match(changedSource.stderr, /Encryption source changed/);
	} finally {
		if (dirname(resolve(root)) !== resolve(tmpdir()) || !basename(root).startsWith('openwebui artifact test ')) throw new Error('Unexpected test directory');
		rmSync(root, { recursive: true });
	}
});
