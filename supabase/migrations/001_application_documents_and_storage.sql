-- 001_application_documents_and_storage.sql
-- Idempotent. Run in the Supabase SQL editor (or your migration tool).
--
-- CONFIRMED: applications(id uuid PK, sme_profile_id uuid FK -> sme_profiles),
--    sme_profiles(id uuid PK, user_id uuid -> auth.uid()).
--
-- The "Design DB schema" task already created public.application_documents
-- (id uuid PK default uuid_generate_v4(), application_id, file_url not null,
-- file_type not null, is_zatca_verified bool default false, uploaded_at
-- default now()), so this does NOT create that table. The existing columns
-- are canonical (see CONVENTIONS.md): file_url, file_type, is_zatca_verified,
-- uploaded_at. This only adds the two columns the upload slice genuinely
-- needs on top of those — filename and status — and leaves everything else
-- untouched. storage_path/content_type/created_at were dropped as redundant
-- with file_url/file_type/uploaded_at; do not reintroduce them. The PK stays
-- "id", not "document_id" — see the DOCUMENTS_ID_COL constant in
-- routers/documents.py.

-- 1) Private Storage bucket -------------------------------------------------
insert into storage.buckets (id, name, public)
values ('application-documents', 'application-documents', false)
on conflict (id) do nothing;

-- 2) application_documents: add the upload-slice's columns -------------------
alter table public.application_documents
    add column if not exists filename text,
    add column if not exists status   text default 'uploaded'
        check (status in ('uploaded', 'processing', 'failed'));

-- application_id is already indexed (idx_app_documents_application from the
-- "Design DB schema" task) — no new index needed.

-- 3) RLS --------------------------------------------------------------------
-- RLS is already enabled on this table (from the "Design DB schema" task).
-- Backend writes with the service-role key (bypasses RLS). This policy only
-- governs direct client reads, so an SME can list their own application's docs.
drop policy if exists "sme reads own application documents" on public.application_documents;
create policy "sme reads own application documents"
    on public.application_documents
    for select
    using (
        exists (
            select 1
            from public.applications a
            join public.sme_profiles p on p.id = a.sme_profile_id
            where a.id = application_documents.application_id
              and p.user_id = auth.uid()
        )
    );

-- 4) Storage RLS (optional) -------------------------------------------------
-- The backend mediates all Storage access via service-role + signed URLs, so
-- broad object policies aren't required. Bucket stays private. Add per-object
-- read policies here later only if you switch to direct-from-client downloads.
