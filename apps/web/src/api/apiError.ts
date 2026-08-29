import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  readonly body: ApiErrorBody;
  readonly status: number;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }

  get retryable(): boolean {
    return this.body.retryable;
  }
}
