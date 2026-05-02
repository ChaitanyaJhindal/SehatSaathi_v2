-- SehatSaathi simple working schema for Supabase dashboard
-- Paste the whole file into Supabase SQL Editor and run it.

begin;

create extension if not exists pgcrypto;

drop table if exists public.reports cascade;
drop table if exists public.patients cascade;
drop table if exists public.doctors cascade;
drop table if exists public.organizations cascade;

create table public.organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now()
);

create table public.doctors (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid references public.organizations(id) on delete set null,
    name text not null,
    specialization text,
    email text unique,
    created_at timestamptz not null default now()
);

create table public.patients (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid not null references public.doctors(id) on delete cascade,
    name text not null,
    age integer,
    gender text,
    created_at timestamptz not null default now(),
    constraint patients_age_chk check (age is null or age between 0 and 150),
    constraint patients_gender_chk check (
        gender is null or gender in ('male', 'female', 'other', 'prefer_not_to_say')
    )
);

create table public.reports (
    id uuid primary key default gen_random_uuid(),
    doctor_id uuid references public.doctors(id) on delete set null,
    patient_id uuid references public.patients(id) on delete set null,
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

create index doctors_organization_id_idx on public.doctors(organization_id);
create index patients_doctor_id_idx on public.patients(doctor_id);
create index reports_doctor_id_idx on public.reports(doctor_id);
create index reports_patient_id_idx on public.reports(patient_id);

alter table public.organizations disable row level security;
alter table public.doctors disable row level security;
alter table public.patients disable row level security;
alter table public.reports disable row level security;

comment on table public.organizations is 'Hospitals or healthcare organizations using SehatSaathi.';
comment on table public.doctors is 'Doctors using SehatSaathi.';
comment on table public.patients is 'Patients linked to doctors.';
comment on table public.reports is 'Generated clinical reports.';

commit;
