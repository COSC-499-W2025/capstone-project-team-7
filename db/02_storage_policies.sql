-- READ own files
create policy "read own objects" on storage.objects
for select to authenticated
using (bucket_id='artifacts'
   and split_part(name,'/',1)=auth.uid()::text);

-- LIST own folder
create policy "list own prefix" on storage.objects
for select to authenticated
using (bucket_id='artifacts'
   and split_part(name,'/',1)=auth.uid()::text);

-- UPLOAD into own folder
create policy "upload to own prefix" on storage.objects
for insert to authenticated
with check (bucket_id='artifacts'
   and split_part(name,'/',1)=auth.uid()::text);

-- UPDATE/DELETE only own files
create policy "modify own objects" on storage.objects
for update to authenticated
using (bucket_id='artifacts' and split_part(name,'/',1)=auth.uid()::text)
with check (bucket_id='artifacts' and split_part(name,'/',1)=auth.uid()::text);

create policy "delete own objects" on storage.objects
for delete to authenticated
using (bucket_id='artifacts' and split_part(name,'/',1)=auth.uid()::text);