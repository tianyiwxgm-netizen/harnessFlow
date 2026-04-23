import axios, { type InternalAxiosRequestConfig } from 'axios';
import { getActivePid } from '@/utils/pid';

export const PID_HEADER = 'X-Harness-Pid';

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10_000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const pid = getActivePid();
  if (pid) {
    config.headers.set(PID_HEADER, pid);
  }
  return config;
});
