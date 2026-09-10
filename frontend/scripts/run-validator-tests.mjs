import assert from 'node:assert';
import { validateYouTubeContent, MAX_SHORT_DURATION_SECONDS } from '../src/lib/youtubeShortsValidator.ts';

console.log('🧪 Running YouTube Shorts & Video Validator Frontend Tests (180s / 3 min limit)...\n');

let passed = 0;
let failed = 0;

function runTest(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ✕ ${name}`);
    console.error(err);
    failed++;
  }
}

// Test 0: Constant check
runTest('Constants: MAX_SHORT_DURATION_SECONDS is 180', () => {
  assert.strictEqual(MAX_SHORT_DURATION_SECONDS, 180);
});

// Test 1: Video selection
runTest('Video selection: standard widescreen video is valid', () => {
  const res = validateYouTubeContent('video', {
    durationSeconds: 300,
    width: 1920,
    height: 1080,
    fileSizeBytes: 100 * 1024 * 1024,
  });

  assert.strictEqual(res.isValid, true);
  assert.strictEqual(res.contentType, 'video');
  assert.strictEqual(res.errors.length, 0);
  assert.strictEqual(res.detectedFormat, 'horizontal');
});

// Test 2: 60 seconds -> valid Short
runTest('Short selection: 60 seconds vertical Short is valid', () => {
  const res = validateYouTubeContent('short', {
    durationSeconds: 60,
    width: 1080,
    height: 1920,
    fileSizeBytes: 15 * 1024 * 1024,
  });

  assert.strictEqual(res.isValid, true);
  assert.strictEqual(res.contentType, 'short');
  assert.strictEqual(res.errors.length, 0);
  assert.strictEqual(res.isShortEligible, true);
  assert.strictEqual(res.detectedFormat, 'vertical');
});

// Test 3: 120 seconds (2 mins) -> valid Short
runTest('Short selection: 120 seconds (2 mins) vertical Short is valid', () => {
  const res = validateYouTubeContent('short', {
    durationSeconds: 120,
    width: 1080,
    height: 1920,
    fileSizeBytes: 25 * 1024 * 1024,
  });

  assert.strictEqual(res.isValid, true);
  assert.strictEqual(res.contentType, 'short');
  assert.strictEqual(res.errors.length, 0);
  assert.strictEqual(res.isShortEligible, true);
});

// Test 4: Exactly 180 seconds (3 mins) -> valid Short
runTest('Short selection: exactly 180 seconds (3 mins) vertical Short is valid', () => {
  const res = validateYouTubeContent('short', {
    durationSeconds: 180,
    width: 1080,
    height: 1920,
    fileSizeBytes: 35 * 1024 * 1024,
  });

  assert.strictEqual(res.isValid, true);
  assert.strictEqual(res.contentType, 'short');
  assert.strictEqual(res.errors.length, 0);
  assert.strictEqual(res.isShortEligible, true);
});

// Test 5: 181 seconds -> invalid Short
runTest('Short selection: 181 seconds (> 3 mins) is invalid', () => {
  const res = validateYouTubeContent('short', {
    durationSeconds: 181,
    width: 1080,
    height: 1920,
    fileSizeBytes: 40 * 1024 * 1024,
  });

  assert.strictEqual(res.isValid, false);
  assert.strictEqual(res.contentType, 'short');
  assert.ok(res.errors.length > 0);
  assert.ok(res.errors[0].includes('3 minutes') || res.errors[0].includes('180 seconds'));
});

// Test 6: Horizontal video -> invalid Short
runTest('Short selection: horizontal video (1920x1080) is invalid', () => {
  const res = validateYouTubeContent('short', {
    durationSeconds: 45,
    width: 1920,
    height: 1080,
    fileSizeBytes: 10 * 1024 * 1024,
  });

  assert.strictEqual(res.isValid, false);
  assert.strictEqual(res.contentType, 'short');
  assert.ok(res.errors.length > 0);
  assert.ok(res.errors[0].includes('aspect ratio'));
  assert.strictEqual(res.detectedFormat, 'horizontal');
});

// Test 7: Video selection with vertical <= 180s produces recommendation warning
runTest('Video selection: vertical video under 180s produces recommendation warning', () => {
  const res = validateYouTubeContent('video', {
    durationSeconds: 90,
    width: 1080,
    height: 1920,
    fileSizeBytes: 18 * 1024 * 1024,
  });

  assert.strictEqual(res.isValid, true);
  assert.ok(res.warnings.length > 0);
  assert.ok(res.warnings[0].includes('YouTube Short'));
});

console.log(`\n📊 Results: ${passed} passed, ${failed} failed.\n`);
if (failed > 0) {
  process.exit(1);
}
