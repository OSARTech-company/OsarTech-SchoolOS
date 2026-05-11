# Complete System Restructuring TODO

## Phase 1: Database & Authentication
- [ ] Create new database schema with roles (super_admin, school_admin, teacher, student)
- [ ] Implement single login system with role detection
- [ ] Create super admin user (osartech3@gmail.com / Stanley2908)
- [ ] Update login page to remove role selection

## Phase 2: Super Admin Features
- [ ] Super admin dashboard
- [ ] Create/Edit schools and school admins
- [ ] View all schools and their statistics

## Phase 3: School Admin Features
- [ ] School admin dashboard
- [ ] Create/Edit teachers and other admins
- [ ] Assign teachers to classes
- [ ] Control school calendar (terms, academic year)
- [ ] Update school logo and information
- [ ] Toggle test/exam score entry on/off
- [ ] Configure max tests (1-5), test scores, exam scores
- [ ] Set exam structure (objective/theory)
- [ ] Student promotion functionality
- [ ] Student ID generation (26/{index}/{first_year_class})

## Phase 4: Teacher Features
- [ ] Teacher dashboard
- [ ] Score entry (CSV or manual)
- [ ] PDF upload for score sheets
- [ ] View assigned classes

## Phase 5: Student Features
- [ ] Student login with ID
- [ ] View/print results
- [ ] Scroll through various results

## Student ID Format Example:
- 26/001/JSS1 (first student in JSS1 who started in 2026)
- 26/015/SSS1 (15th student in SSS1 who started in 2026)
