-- VeriFinder stores generated reports separately from the bulk public-data lake.
-- The backend is the only client of this private bucket and issues short-lived links.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'verifinder-reports',
  'verifinder-reports',
  false,
  10485760,
  array['application/pdf']
)
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
