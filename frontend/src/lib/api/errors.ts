// Mirrors the error envelope in docs/API.md §4 exactly — the backend never
// sends a stack trace or raw exception, only these four fields. Switch on
// `errorCode`, never on `message` text (message is safe UI copy, not a
// stable identifier — see backend app/shared/errors.py).

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string;
  readonly requestId: string;
  readonly details: Record<string, unknown>;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.status = status;
    this.errorCode = body.error_code;
    this.requestId = body.request_id;
    this.details = body.details ?? {};
  }
}

interface ApiErrorBody {
  error_code: string;
  message: string;
  request_id: string;
  details?: Record<string, unknown>;
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}
