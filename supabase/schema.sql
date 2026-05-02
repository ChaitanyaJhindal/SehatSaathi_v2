-- SehatSaathi Supabase schema
-- Run this in the Supabase SQL Editor or as a migration.

begin;

create extension if not exists pgcrypto;

create table if not exists public.organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now()
);

create table if not exists public.doctors (
    id uuid primary key references auth.users (id) on delete cascade,
    organization_id uuid not null references public.organizations (id) on delete cascade,
    name text not null,
    specialization text,
    email text not null unique,
    created_at timestamptz not null default now(),
    constraint doctors_email_format_chk check (position('@' in email) > 1)
);

create table if not exists public.patients (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references public.doctors (id) on delete cascade,
    name text not null,
    age integer,
    gender text,
    created_at timestamptz not null default now(),
    constraint patients_age_chk check (age is null or age between 0 and 150),
    constraint patients_gender_chk check (
        gender is null or gender in ('male', 'female', 'other', 'prefer_not_to_say')
    )
);

create table if not exists public.reports (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references public.doctors (id) on delete cascade,
    patient_id uuid references public.patients (id) on delete set null,
    transcript text,
    symptoms jsonb not null default '[]'::jsonb,
    diagnosis text,
    medications jsonb not null default '[]'::jsonb,
    dosage jsonb not null default '[]'::jsonb,
    precautions jsonb not null default '[]'::jsonb,
    doctor_notes text,
    pdf_url text,
    created_at timestamptz not null default now(),
    constraint reports_symptoms_array_chk check (jsonb_typeof(symptoms) = 'array'),
    constraint reports_medications_array_chk check (jsonb_typeof(medications) = 'array'),
    constraint reports_dosage_array_chk check (jsonb_typeof(dosage) = 'array'),
    constraint reports_precautions_array_chk check (jsonb_typeof(precautions) = 'array')
);

create index if not exists doctors_organization_id_idx
    on public.doctors (organization_id);

create index if not exists patients_doctor_id_idx
    on public.patients (doctor_id);

create index if not exists reports_doctor_id_idx
    on public.reports (doctor_id);

create index if not exists reports_patient_id_idx
    on public.reports (patient_id);

alter table public.organizations enable row level security;
alter table public.doctors enable row level security;
alter table public.patients enable row level security;
alter table public.reports enable row level security;

drop policy if exists "Doctors can view own organization" on public.organizations;
create policy "Doctors can view own organization"
on public.organizations
for select
to authenticated
using (
    exists (
        select 1
        from public.doctors d
        where d.id = auth.uid()
          and d.organization_id = organizations.id
    )
);

drop policy if exists "Doctors can view own row" on public.doctors;
create policy "Doctors can view own row"
on public.doctors
for select
to authenticated
using (id = auth.uid());

drop policy if exists "Doctors can insert own row" on public.doctors;
create policy "Doctors can insert own row"
on public.doctors
for insert
to authenticated
with check (id = auth.uid());

drop policy if exists "Doctors can update own row" on public.doctors;
create policy "Doctors can update own row"
on public.doctors
for update
to authenticated
using (id = auth.uid())
with check (id = auth.uid());

drop policy if exists "Doctors can delete own row" on public.doctors;
create policy "Doctors can delete own row"
on public.doctors
for delete
to authenticated
using (id = auth.uid());

drop policy if exists "Doctors can manage own patients" on public.patients;
create policy "Doctors can manage own patients"
on public.patients
for all
to authenticated
using (doctor_id = auth.uid())
with check (doctor_id = auth.uid());

drop policy if exists "Doctors can manage own reports" on public.reports;
create policy "Doctors can manage own reports"
on public.reports
for all
to authenticated
using (doctor_id = auth.uid())
with check (doctor_id = auth.uid());

insert into storage.buckets (id, name, public)
values ('reports', 'reports', true)
on conflict (id) do update
set public = excluded.public;

drop policy if exists "Public can view report PDFs" on storage.objects;
create policy "Public can view report PDFs"
on storage.objects
for select
to public
using (bucket_id = 'reports');

drop policy if exists "Doctors can upload own report PDFs" on storage.objects;
create policy "Doctors can upload own report PDFs"
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'reports'
    and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "Doctors can update own report PDFs" on storage.objects;
create policy "Doctors can update own report PDFs"
on storage.objects
for update
to authenticated
using (
    bucket_id = 'reports'
    and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
    bucket_id = 'reports'
    and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "Doctors can delete own report PDFs" on storage.objects;
create policy "Doctors can delete own report PDFs"
on storage.objects
for delete
to authenticated
using (
    bucket_id = 'reports'
    and (storage.foldername(name))[1] = auth.uid()::text
);

comment on table public.organizations is 'Hospitals or healthcare organizations using SehatSaathi.';
comment on table public.doctors is 'Doctor profiles mapped 1:1 to Supabase auth.users.';
comment on table public.patients is 'Patients owned by an individual doctor.';
comment on table public.reports is 'Structured clinical reports generated from voice workflows.';

commit;

-- Optional sample inserts
-- insert into public.organizations (name) values ('City Hospital');
-- insert into public.doctors (id, organization_id, name, specialization, email)
-- values ('<auth_user_uuid>', '<organization_uuid>', 'Dr. Sharma', 'Cardiology', 'dr.sharma@example.com');
-- insert into public.patients (doctor_id, name, age, gender)
-- values ('<auth_user_uuid>', 'Aman Verma', 42, 'male');
-- insert into public.reports (doctor_id, patient_id, transcript, symptoms, diagnosis, medications, dosage, precautions, doctor_notes, pdf_url)
-- values (
--     '<auth_user_uuid>',
--     '<patient_uuid>',
--     'Patient reports chest pain and dry cough.',
--     '["chest pain", "dry cough"]'::jsonb,
--     'Possible viral infection',
--     '["Paracetamol"]'::jsonb,
--     '["500mg twice daily"]'::jsonb,
--     '["Rest", "Hydration"]'::jsonb,
--     'Monitor symptoms for 3 days',
--     'https://<project>.supabase.co/storage/v1/object/public/reports/<doctor_id>/<report_id>.pdf'
-- );
