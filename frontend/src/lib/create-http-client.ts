import axios, { AxiosError, type CreateAxiosDefaults } from "axios";

import { buildApiError, buildNetworkError, type BackendErrorEnvelope } from "@/lib/http-error";

/**
 * Wires the shared error-normalization response interceptor onto a new
 * Axios instance, so every HTTP client in the app (the direct backend
 * client and the same-origin BFF client) rejects with one consistent
 * ApiError shape instead of each re-implementing the interceptor.
 */
export function createHttpClient(config: CreateAxiosDefaults) {
  const instance = axios.create(config);

  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError<BackendErrorEnvelope>) => {
      if (!error.response) {
        return Promise.reject(
          buildNetworkError(error.message || "Unable to reach the server.", error.code ?? "NETWORK_ERROR")
        );
      }
      return Promise.reject(buildApiError(error.response.status, error.response.data));
    }
  );

  return instance;
}
