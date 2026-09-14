/**
 * ContentPilot API Client
 * Connects Next.js Frontend to FastAPI Backend
 */

export interface LearnerProfile {
  age_group: string;
  education_level: string;
  language_background: string;
  vocabulary_level: string;
  career_goal: string;
  country: string;
}

export interface CreateRunRequest {
  topic: string;
  learner_profile: LearnerProfile;
  demo_mode?: string | null;
}

export interface RunSummary {
  run_id: string;
  topic: string;
  final_status: string;
  retry_count: number;
  lesson_version: number;
  created_at?: string;
  completed_at?: string;
}

export interface LessonSection {
  heading: string;
  content: string;
  key_takeaways?: string[];
}

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_option_index: number;
  explanation: string;
}

export interface LessonData {
  title: string;
  target_audience: string;
  sections: LessonSection[];
  summary: string;
  quiz: QuizQuestion[];
  vocabulary_definitions?: Record<string, string>;
}

export interface EvaluationCheck {
  layer: string;
  check_name: string;
  dimension?: string;
  passed: boolean;
  severity: string;
  reason: string;
  evidence?: string;
  suggested_correction?: string;
}

export interface EvaluationAttempt {
  attempt_number: number;
  passed: boolean;
  checks: EvaluationCheck[];
  timestamp?: string;
}

export interface RunDetail {
  run_id: string;
  topic: string;
  learner_profile: LearnerProfile;
  final_status: string;
  retry_count: number;
  lesson_version: number;
  lesson_versions_count: number;
  curriculum_plan?: {
    topic: string;
    modules: string[];
    prerequisites: string[];
    learning_objectives: string[];
  };
  learning_objectives: string[];
  evaluation_result?: {
    overall_passed: boolean;
    layer_summaries: Record<string, { passed: boolean; failures_count: number }>;
  };
  metrics: Record<string, any>;
  prompt_version: string;
  rubric_version: string;
  model_version: string;
  error?: string;
  created_at?: string;
  completed_at?: string;
  attempts?: EvaluationAttempt[];
}

export interface HealthStatus {
  status: string;
  version: string;
  database: string;
  pgvector: string;
}

export interface IngestResponse {
  status: string;
  documents: number;
  chunks: number;
  kb_version: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!res.ok) {
      const errorText = await res.text();
      let parsedMessage = errorText;
      try {
        const jsonErr = JSON.parse(errorText);
        if (jsonErr.message) {
          parsedMessage = jsonErr.message;
        } else if (Array.isArray(jsonErr.detail)) {
          parsedMessage = jsonErr.detail
            .map((d: any) => `${d.loc ? d.loc.slice(1).join(".") : "field"}: ${d.msg}`)
            .join("; ");
        } else if (typeof jsonErr.detail === "string") {
          parsedMessage = jsonErr.detail;
        }
      } catch {
        // Raw text response
      }
      const formattedError = `API Error (${res.status}): ${parsedMessage}`;
      console.error(`[ContentPilot API Error] ${endpoint}:`, {
        status: res.status,
        message: parsedMessage,
        raw: errorText,
      });
      throw new Error(formattedError);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`[ContentPilot Client Error] ${endpoint}:`, err.message || err);
    throw err;
  }
}

export const api = {
  getHealth: (): Promise<HealthStatus> => fetchJson<HealthStatus>("/health"),

  createRun: (payload: CreateRunRequest): Promise<{ run_id: string; status: string }> =>
    fetchJson<{ run_id: string; status: string }>("/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listRuns: (limit: number = 20): Promise<RunSummary[]> =>
    fetchJson<RunSummary[]>(`/runs?limit=${limit}`),

  getRunDetail: (runId: string): Promise<RunDetail> =>
    fetchJson<RunDetail>(`/runs/${runId}`),

  getLesson: (runId: string, version?: number): Promise<{ run_id: string; lesson_version: number; lesson: LessonData; status: string }> =>
    fetchJson<{ run_id: string; lesson_version: number; lesson: LessonData; status: string }>(
      `/runs/${runId}/lesson${version ? `?version=${version}` : ""}`
    ),

  getRejectionLog: (runId: string): Promise<any> =>
    fetchJson<any>(`/runs/${runId}/rejection-log`),

  getEvolutionStatus: (): Promise<any> =>
    fetchJson<any>("/evolution/status"),

  proposeEvolution: (payload: { prompt_name: string; current_version: string; improvement: string; new_template: string }): Promise<any> =>
    fetchJson<any>("/evolution/propose", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  ingestKnowledge: (documentsDir = "knowledge/documents", metadataPath = "knowledge/metadata.json"): Promise<IngestResponse> =>
    fetchJson<IngestResponse>("/knowledge/ingest", {
      method: "POST",
      body: JSON.stringify({ documents_dir: documentsDir, metadata_path: metadataPath }),
    }),
};
