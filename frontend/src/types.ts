export type MatchStatus = 'matched' | 'review' | 'unmatched';

export interface MatchCandidate {
  catalog_id: number;
  title: string;
  author: string;
  score: number;
}

export interface Match {
  status: MatchStatus;
  best_match: MatchCandidate | null;
  candidates: MatchCandidate[];
}

export interface SpineRead {
  title: string;
  author: string;
  legible: boolean;
}

export interface ScannedBook {
  index: number;
  bbox: [number, number, number, number];
  crop_url: string | null;
  detection_score: number;
  read: SpineRead;
  match: Match;
}

export interface ScanTiming {
  detection_seconds?: number;
  vlm_seconds?: number;
  vlm_input_tokens?: number | null;
  vlm_output_tokens?: number | null;
}

export interface ScanResponse {
  warnings: string[];
  books: ScannedBook[];
  timing: ScanTiming;
}

export interface LibraryEntry {
  id: number;
  title: string;
  author: string;
  catalog_id: number | null;
  match_confidence: number | null;
  added_at: string;
}
