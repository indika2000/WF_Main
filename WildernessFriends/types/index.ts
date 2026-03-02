export interface ScanResult {
  value: string;
  type: string;
  timestamp: number;
}

export interface User {
  uid: string;
  email: string | null;
}
