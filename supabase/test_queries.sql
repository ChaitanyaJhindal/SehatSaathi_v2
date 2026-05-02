-- Run this after schema.sql in Supabase SQL Editor

begin;

with inserted_org as (
    insert into public.organizations (name)
    values ('SehatSaathi Demo Hospital')
    returning id
),
inserted_doctor as (
    insert into public.doctors (organization_id, name, specialization, email)
    select id, 'Dr. Meera Sharma', 'General Medicine', 'meera.sharma@example.com'
    from inserted_org
    returning id
)
insert into public.patients (doctor_id, name, age, gender)
select id, 'Aman Verma', 42, 'male'
from inserted_doctor;

commit;

select 'organizations' as table_name, count(*) as total_rows from public.organizations
union all
select 'doctors', count(*) from public.doctors
union all
select 'patients', count(*) from public.patients
union all
select 'reports', count(*) from public.reports;

select
    p.id as patient_id,
    p.name as patient_name,
    p.age,
    p.gender,
    d.id as doctor_id,
    d.name as doctor_name
from public.patients p
left join public.doctors d on d.id = p.doctor_id
order by p.created_at desc
limit 5;
