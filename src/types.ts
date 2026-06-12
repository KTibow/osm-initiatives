export type PullRef = {
  owner: string;
  repo: string;
  number: number;
  initiative: string;
  label?: string;
};

export type PullSnapshot = PullRef & {
  title: string;
  url: string;
  state: string;
  draft: boolean;
  labels: string[];
  openedAt: string;
  updatedAt: string;
  headSha: string;
  merged: boolean;
  mergeableState: string | null;
  requestedReviewers: string[];
  checks: "success" | "pending" | "failure" | "error" | "unknown";
  ageDays: number;
  error?: string;
};

export type EliLayerWatch = {
  id: string;
  name: string;
  country?: string;
  prs: number[];
  note: string;
};

export type EliAvailabilityLayer = {
  id: string;
  name: string;
  countryCode?: string;
  category?: string;
  type?: string;
  status: string;
  okSamples: number;
  samples: number;
  exampleStatus?: string;
  exampleHttpStatus?: string;
  exampleDetail?: string;
  exampleUrl?: string;
  declaredZoomExampleStatus?: string;
  declaredZoomExampleDetail?: string;
  declaredZoomExampleUrl?: string;
  workingZoom?: number | null;
  maxZoom?: number | null;
  sourcePath?: string;
};

export type EliAvailability = {
  generatedAt: string;
  layers: EliAvailabilityLayer[];
};

export type OverpassElement = {
  type: "node" | "way" | "relation";
  id: number;
  lat?: number;
  lon?: number;
  tags?: Record<string, string>;
  center?: { lat: number; lon: number };
};

export type OverpassSnapshot = {
  elements: OverpassElement[];
  fetchedAt: string;
  error?: string;
  remark?: string;
};
