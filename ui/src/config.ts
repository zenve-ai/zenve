export default {
  appName: (import.meta.env.VITE_APP_NAME as string) || 'zenve',
  apiUrl: (import.meta.env.VITE_API_URL as string) || '/api',
  runtimeUrl: (import.meta.env.VITE_RUNTIME_URL as string) || '/api/v1',
  tokenKey: (import.meta.env.VITE_TOKEN_KEY as string) || 'app-token',
  userKey: (import.meta.env.VITE_USER_KEY as string) || 'app-user',
  isProd: import.meta.env.PROD,
}
