"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

export function DatasetSearchForm({
  initialValue = "",
  action,
  label,
  placeholder,
}: {
  initialValue?: string;
  action: string;
  label: string;
  placeholder: string;
}) {
  const router = useRouter();
  const [query, setQuery] = useState(initialValue);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (value.length >= 2) router.push(`${action}?q=${encodeURIComponent(value)}`);
  }

  return (
    <form className="search-form dataset-search-form" onSubmit={submit} role="search">
      <Search className="search-leading" size={21} aria-hidden="true" />
      <label className="sr-only" htmlFor={`${action}-search`}>{label}</label>
      <input
        id={`${action}-search`}
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={placeholder}
        autoComplete="off"
      />
      <button type="submit" aria-label={label}><Search size={20} /></button>
    </form>
  );
}
