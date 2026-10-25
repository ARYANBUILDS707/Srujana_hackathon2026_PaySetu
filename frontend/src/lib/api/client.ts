// The only place that calls `fetch` (or XMLHttpRequest, for upload progress) (AGENTS.md 4). Requests go to the same origin;
// in development Next.js proxies /api/* to the backend. No secrets exist in the browser.

export interface FieldError {
  field: string;
  code: string;
  message: string;
}

/** A failed API call, parsed from the backend's `application/problem+json` response. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly fieldErrors: FieldError[] = [],
    readonly requestId: string | null = null,
    /** Seconds from a 429's Retry-After header, when present. */
    readonly retryAfterSeconds: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** Message for one form field, if the server reported one. */
  forField(field: string): string | undefined {
    return this.fieldErrors.find((e) => e.field === field)?.message;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT";
  json?: unknown;
  form?: FormData;
}

/** Fired when a signed-in request gets 401: the session expired, was revoked or is missing. */
export const SESSION_ENDED_EVENT = "paysetu:session-ended";

function reportSessionEnded(path: string, error: ApiError) {
  // Auth endpoints report 401 themselves (e.g. a wrong password); everything else means the
  // session is gone. The session provider listens and sends the user to the login page.
  if (error.status === 401 && !path.startsWith("/auth/") && typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(SESSION_ENDED_EVENT, { detail: error.code }));
  }
}

export function asApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  return new ApiError(0, "unknown", "Something went wrong. Please try again.");
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };
  // Required by the backend's CSRF check on unsafe methods (API.md Section 1.2).
  if (method !== "GET") headers["X-PaySetu-Client"] = "web";
  let body: BodyInit | undefined;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    body = options.form;
  }

  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { method, headers, body, cache: "no-store" });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Could not reach the PaySetu server. Check that the API is running and try again.",
    );
  }

  if (!response.ok) {
    const error = await problemFrom(response);
    reportSessionEnded(path, error);
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function problemFrom(response: Response): Promise<ApiError> {
  try {
    const problem = (await response.json()) as {
      code?: string;
      detail?: string;
      title?: string;
      errors?: FieldError[];
      request_id?: string | null;
    };
    return new ApiError(
      response.status,
      problem.code ?? "http_error",
      problem.detail ?? problem.title ?? "The request failed.",
      problem.errors ?? [],
      problem.request_id ?? response.headers.get("x-request-id"),
      Number(response.headers.get("retry-after")) || null,
    );
  } catch {
    return new ApiError(response.status, "http_error", "The request failed.");
  }
}

export interface Download {
  blob: Blob;
  filename: string;
  packSha256: string | null;
}

/** GET a file. Errors arrive as problem+json and are thrown as `ApiError`, like `api()`. */
export async function apiDownload(path: string): Promise<Download> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Could not reach the PaySetu server. Check that the API is running and try again.",
    );
  }
  if (!response.ok) {
    const error = await problemFrom(response);
    reportSessionEnded(path, error);
    throw error;
  }

  const disposition = response.headers.get("content-disposition") ?? "";
  const named = /filename="([^"]+)"/.exec(disposition)?.[1] ?? "paysetu-download.zip";
  return {
    blob: await response.blob(),
    // Only a plain file name is ever used for the saved file.
    filename: named.replace(/[^A-Za-z0-9._-]/g, "_"),
    packSha256: response.headers.get("x-paysetu-pack-sha256"),
  };
}

/**
 * POST multipart form data with upload progress (0 to 1). Same CSRF header, error format and
 * session handling as `api()`; uses XMLHttpRequest because fetch cannot report upload progress.
 */
export function apiUpload<T>(
  path: string,
  form: FormData,
  onProgress: (fraction: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `/api/v1${path}`);
    request.setRequestHeader("Accept", "application/json");
    request.setRequestHeader("X-PaySetu-Client", "web");
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    request.onerror = () =>
      reject(
        new ApiError(
          0,
          "network_error",
          "Could not reach the PaySetu server. Check that the API is running and try again.",
        ),
      );
    request.onload = () => {
      const response = new Response(request.responseText, {
        status: request.status,
        headers: { "retry-after": request.getResponseHeader("retry-after") ?? "" },
      });
      if (request.status >= 200 && request.status < 300) {
        resolve(JSON.parse(request.responseText) as T);
        return;
      }
      void problemFrom(response).then((error) => {
        reportSessionEnded(path, error);
        reject(error);
      });
    };
    request.send(form);
  });
}
