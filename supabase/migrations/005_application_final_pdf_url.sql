-- 005_application_final_pdf_url.sql
--
-- applications.final_pdf_url — where application_builder_node files the Arabic
-- PDF it renders (core/application_builder.py).
--
-- GET /api/v1/applications/{id}/pdf has read this column since the endpoint was
-- stubbed (routers/applications.py), but no migration ever added it — the column
-- did not exist. Adding it here, in the commit that first writes to it.
--
-- It holds the BARE Storage object path (e.g. "<application_id>/report.pdf") in
-- the existing private `application-documents` bucket — the same convention as
-- application_documents.file_url, and for the same reason: the path is stable
-- while a signed URL expires. The endpoint signs it on read.
--
-- No new bucket: the backend mediates every Storage read via service-role signed
-- URLs, so a second bucket would add an RLS surface and buy nothing.

alter table public.applications
    add column if not exists final_pdf_url text;

comment on column public.applications.final_pdf_url is
    'Supabase Storage object path of the generated Arabic application report PDF, '
    'in the application-documents bucket. Written by application_builder_node; '
    'signed on read by GET /api/v1/applications/{id}/pdf. NULL until the graph runs.';
