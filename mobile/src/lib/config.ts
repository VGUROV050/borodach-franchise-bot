// App configuration
//
// API_URL — backend mobile API base URL (no trailing slash)
// PARTNER_ID — hardcoded for TestFlight MVP; will be replaced by auth later

export const API_URL = __DEV__
  ? "http://localhost:8001"
  : "https://api.borodach-franchise.ru";

export const PARTNER_ID = 1;
