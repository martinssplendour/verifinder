import type { SourceAttribution } from "./common";

export interface CountryOption {
  code: string;
  name: string;
}

export interface BrowseDataset {
  id: string;
  label: string;
  description: string;
  organisation: string;
  /** Null when the register holds no place, so no location filter applies. */
  place_label: string | null;
  countries: string[];
  imported: boolean;
  message: string | null;
}

export interface BrowseCatalogue {
  countries: CountryOption[];
  datasets: BrowseDataset[];
}

export interface BrowseRecord {
  id: string;
  title: string;
  subtitle: string | null;
  place: string | null;
  href: string;
}

export interface BrowseResponse {
  dataset: string;
  country: string | null;
  place: string | null;
  page: number;
  page_size: number;
  total: number;
  records: BrowseRecord[];
  dataset_version: string | null;
  source: SourceAttribution | null;
  message: string | null;
}
