export type YouTubeContentType = 'video' | 'short';

export const MAX_SHORT_DURATION_SECONDS = 180;

export interface YouTubeValidationMetadata {
  durationSeconds?: number | null;
  width?: number | null;
  height?: number | null;
  fileSizeBytes?: number | null;
}

export interface YouTubeValidationResult {
  isValid: boolean;
  contentType: YouTubeContentType;
  errors: string[];
  warnings: string[];
  isShortEligible: boolean;
  aspectRatio: number | null;
  detectedFormat: 'vertical' | 'square' | 'horizontal' | 'unknown';
}

/**
 * Validate YouTube video assets for standard Videos vs YouTube Shorts.
 * YouTube Shorts Requirements:
 * - Aspect Ratio: Vertical (9:16) or Square (1:1), i.e., width <= height * 1.05.
 * - Duration: 180 seconds (3 minutes) or less.
 */
export function validateYouTubeContent(
  contentType: YouTubeContentType,
  metadata: YouTubeValidationMetadata
): YouTubeValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  const { durationSeconds, width, height } = metadata;

  let aspectRatio: number | null = null;
  let detectedFormat: 'vertical' | 'square' | 'horizontal' | 'unknown' = 'unknown';

  if (width && height && height > 0) {
    aspectRatio = width / height;
    if (aspectRatio <= 0.65) {
      detectedFormat = 'vertical'; // e.g. 9:16 is 0.5625
    } else if (aspectRatio <= 1.05) {
      detectedFormat = 'square'; // 1:1
    } else {
      detectedFormat = 'horizontal'; // e.g. 16:9 is 1.777
    }
  }

  const isDurationEligibleForShorts =
    durationSeconds === null ||
    durationSeconds === undefined ||
    durationSeconds <= MAX_SHORT_DURATION_SECONDS + 0.5;

  const isDimensionsEligibleForShorts =
    width === null ||
    width === undefined ||
    height === null ||
    height === undefined ||
    width <= height * 1.05;

  const isShortEligible = isDurationEligibleForShorts && isDimensionsEligibleForShorts;

  if (contentType === 'short') {
    // 1. Validate Duration (must be <= 180 seconds / 3 minutes)
    if (durationSeconds !== null && durationSeconds !== undefined) {
      if (durationSeconds > MAX_SHORT_DURATION_SECONDS + 0.5) {
        errors.push(
          `YouTube Shorts must be 3 minutes (${MAX_SHORT_DURATION_SECONDS} seconds) or less. Your video is ${Math.round(
            durationSeconds
          )} seconds long.`
        );
      }
    }

    // 2. Validate Dimensions / Aspect Ratio
    if (width && height) {
      if (width > height * 1.05) {
        errors.push(
          `YouTube Shorts must have a vertical (9:16) or square (1:1) aspect ratio. Your video is horizontal widescreen (${width}×${height}).`
        );
      }
    }
  } else {
    // contentType === 'video'
    if (
      isShortEligible &&
      durationSeconds &&
      durationSeconds <= MAX_SHORT_DURATION_SECONDS &&
      width &&
      height &&
      width < height
    ) {
      warnings.push(
        'This video is vertical and 3 minutes or less. You can publish it as a YouTube Short for higher mobile reach.'
      );
    }
  }

  return {
    isValid: errors.length === 0,
    contentType,
    errors,
    warnings,
    isShortEligible,
    aspectRatio,
    detectedFormat,
  };
}
