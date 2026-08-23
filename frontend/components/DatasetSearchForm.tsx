"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

export function DatasetSearchForm({
  initialValue = "",
  action,
  label,
  placeholder,
  queryParam = "q",
  retainedParams = {},
}: {
  initialValue?: string;
  action: string;
  label: string;
  placeholder: string;
  queryParam?: string;
  retainedParams?: Record<string, string>;
}) {
  const router = useRouter();
  const [query, setQuery] = useState(initialValue);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (value.length < 2) return;
    const params = new URLSearchParams(retainedParams);
    params.set(queryParam, value);
    router.push(`${action}?${params.toString()}`);
  }

  const inputId = `${action}-${queryParam}-search`.replaceAll("/", "-");

  return (
    <form className="search-form dataset-search-form" onSubmit={submit} role="search">
      <Search className="search-leading" size={21} aria-hidden="true" />
      <label className="sr-only" htmlFor={inputId}>{label}</label>
      <input
        id={inputId}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={placeholder}
        autoComplete="off"
      />
      <button type="submit" aria-label={label}><Search size={20} /></button>
    </form>
  );
}
