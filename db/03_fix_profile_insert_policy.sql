create policy "insert own profile" on public.profiles 
for insert 
with check (id = auth.uid());