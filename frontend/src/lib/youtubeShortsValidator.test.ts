import { validateYouTubeContent, MAX_SHORT_DURATION_SECONDS } from './youtubeShortsValidator';

describe('YouTube Content & Shorts Validator', () => {
  test('Constants: MAX_SHORT_DURATION_SECONDS is 180', () => {
    expect(MAX_SHORT_DURATION_SECONDS).toBe(180);
  });

  // Test 1: Video selection
  test('Video selection: standard widescreen video is valid', () => {
    const res = validateYouTubeContent('video', {
      durationSeconds: 300,
      width: 1920,
      height: 1080,
      fileSizeBytes: 100 * 1024 * 1024,
    });

    expect(res.isValid).toBe(true);
    expect(res.contentType).toBe('video');
    expect(res.errors.length).toBe(0);
    expect(res.detectedFormat).toBe('horizontal');
  });

  // Test 2: 60 seconds -> valid Short
  test('Short selection: 60 seconds vertical Short is valid', () => {
    const res = validateYouTubeContent('short', {
      durationSeconds: 60,
      width: 1080,
      height: 1920,
      fileSizeBytes: 15 * 1024 * 1024,
    });

    expect(res.isValid).toBe(true);
    expect(res.contentType).toBe('short');
    expect(res.errors.length).toBe(0);
    expect(res.isShortEligible).toBe(true);
    expect(res.detectedFormat).toBe('vertical');
  });

  // Test 3: 120 seconds (2 mins) -> valid Short
  test('Short selection: 120 seconds (2 mins) vertical Short is valid', () => {
    const res = validateYouTubeContent('short', {
      durationSeconds: 120,
      width: 1080,
      height: 1920,
      fileSizeBytes: 25 * 1024 * 1024,
    });

    expect(res.isValid).toBe(true);
    expect(res.contentType).toBe('short');
    expect(res.errors.length).toBe(0);
    expect(res.isShortEligible).toBe(true);
  });

  // Test 4: Exactly 180 seconds (3 mins) -> valid Short
  test('Short selection: exactly 180 seconds (3 mins) vertical Short is valid', () => {
    const res = validateYouTubeContent('short', {
      durationSeconds: 180,
      width: 1080,
      height: 1920,
      fileSizeBytes: 35 * 1024 * 1024,
    });

    expect(res.isValid).toBe(true);
    expect(res.contentType).toBe('short');
    expect(res.errors.length).toBe(0);
    expect(res.isShortEligible).toBe(true);
  });

  // Test 5: 181 seconds -> invalid Short
  test('Short selection: 181 seconds (> 3 mins) is invalid', () => {
    const res = validateYouTubeContent('short', {
      durationSeconds: 181,
      width: 1080,
      height: 1920,
      fileSizeBytes: 40 * 1024 * 1024,
    });

    expect(res.isValid).toBe(false);
    expect(res.contentType).toBe('short');
    expect(res.errors.length).toBeGreaterThan(0);
    expect(res.errors[0]).toContain('3 minutes');
    expect(res.errors[0]).toContain('180 seconds');
  });

  // Test 6: Horizontal video -> invalid Short
  test('Short selection: horizontal video (1920x1080) is invalid', () => {
    const res = validateYouTubeContent('short', {
      durationSeconds: 45,
      width: 1920,
      height: 1080,
      fileSizeBytes: 10 * 1024 * 1024,
    });

    expect(res.isValid).toBe(false);
    expect(res.contentType).toBe('short');
    expect(res.errors.length).toBeGreaterThan(0);
    expect(res.errors[0]).toContain('aspect ratio');
    expect(res.detectedFormat).toBe('horizontal');
  });

  // Test 7: Video selection with vertical <= 180s produces recommendation warning
  test('Video selection: vertical video under 180s produces recommendation warning', () => {
    const res = validateYouTubeContent('video', {
      durationSeconds: 90,
      width: 1080,
      height: 1920,
      fileSizeBytes: 18 * 1024 * 1024,
    });

    expect(res.isValid).toBe(true);
    expect(res.warnings.length).toBeGreaterThan(0);
    expect(res.warnings[0]).toContain('YouTube Short');
  });
});
