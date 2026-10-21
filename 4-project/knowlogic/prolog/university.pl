/* KnowLogic AI - university.pl
   SWI-Prolog knowledge base + rules for the university domain.
   Facts mirror knowlogic/kb.py load_sample_kb(); rules mirror
   knowlogic/engine.py (R1-R8). Run:
     swipl -s university.pl
     ?- eligible(ayesha, 'AI301').        % true
     ?- missing_prereqs(ali, 'AI301', M). % M = ['CS201','MATH201']
*/

:- dynamic student/4, instructor/3, course/4, completed/2, enrolled/2,
           teaches/2, prerequisite/2.

student(ali, 'Ali Raza', 'Computer Science', 5).
student(ayesha, 'Ayesha Khan', 'Artificial Intelligence', 7).
student(hassan, 'Hassan Ali', 'Computer Science', 3).
student(zara, 'Zara Iqbal', 'Computer Science', 5).
student(omar, 'Omar Farooq', 'Artificial Intelligence', 3).
student(danish, 'Danish Mehmood', 'Computer Science', 3).
student(kinza, 'Kinza Tariq', 'Artificial Intelligence', 5).
student(shayan, 'Shayan Ahmed', 'Computer Science', 7).
student(mahnoor, 'Mahnoor Fatima', 'Mathematics', 3).
student(usama, 'Usama Khalid', 'Computer Science', 1).
student(iqra, 'Iqra Aziz', 'Artificial Intelligence', 7).
student(hamza, 'Hamza Sheikh', 'Computer Science', 5).
instructor(dr_ahmed, 'Dr. Ahmed Khan', 'Computer Science').
instructor(dr_sara, 'Dr. Sara Malik', 'Artificial Intelligence').
instructor(dr_bilal, 'Dr. Bilal Ahmed', 'Mathematics').
instructor(dr_fatima, 'Dr. Fatima Noor', 'Computer Science').
instructor(dr_usman, 'Dr. Usman Tariq', 'Computer Science').
instructor(dr_maryam, 'Dr. Maryam Aslam', 'Artificial Intelligence').
course('CS101', 'Introduction to Programming', 'Computer Science', 3).
course('CS102', 'Data Structures', 'Computer Science', 3).
course('CS201', 'Algorithms', 'Computer Science', 3).
course('CS202', 'Operating Systems', 'Computer Science', 3).
course('CS305', 'Database Systems', 'Computer Science', 3).
course('CS310', 'Computer Networks', 'Computer Science', 3).
course('CS320', 'Software Engineering', 'Computer Science', 3).
course('MATH101', 'Calculus I', 'Mathematics', 3).
course('MATH201', 'Statistics', 'Mathematics', 3).
course('MATH301', 'Linear Algebra', 'Mathematics', 3).
course('AI301', 'Machine Learning', 'Artificial Intelligence', 3).
course('AI302', 'Natural Language Processing', 'Artificial Intelligence', 3).
course('AI303', 'Computer Vision', 'Artificial Intelligence', 3).
course('AI305', 'Data Science', 'Artificial Intelligence', 4).
course('AI401', 'Deep Learning', 'Artificial Intelligence', 4).
completed(ali, 'CS101').
completed(ali, 'CS102').
completed(ali, 'MATH101').
completed(ayesha, 'CS101').
completed(ayesha, 'CS102').
completed(ayesha, 'CS201').
completed(ayesha, 'MATH101').
completed(ayesha, 'MATH201').
completed(danish, 'CS101').
completed(hamza, 'CS101').
completed(hamza, 'CS102').
completed(hassan, 'CS101').
completed(iqra, 'AI301').
completed(iqra, 'CS101').
completed(iqra, 'CS102').
completed(iqra, 'CS201').
completed(iqra, 'MATH101').
completed(iqra, 'MATH201').
completed(kinza, 'CS101').
completed(kinza, 'CS102').
completed(kinza, 'MATH101').
completed(kinza, 'MATH201').
completed(mahnoor, 'MATH101').
completed(omar, 'CS101').
completed(shayan, 'CS101').
completed(shayan, 'CS102').
completed(shayan, 'CS201').
completed(shayan, 'MATH101').
completed(zara, 'CS101').
completed(zara, 'CS102').
completed(zara, 'MATH101').
enrolled(ali, 'CS201').
enrolled(ayesha, 'AI301').
enrolled(danish, 'CS102').
enrolled(danish, 'MATH101').
enrolled(hamza, 'CS201').
enrolled(hamza, 'CS320').
enrolled(hassan, 'CS102').
enrolled(iqra, 'AI302').
enrolled(iqra, 'AI401').
enrolled(kinza, 'AI305').
enrolled(kinza, 'CS201').
enrolled(mahnoor, 'CS101').
enrolled(mahnoor, 'MATH201').
enrolled(omar, 'CS102').
enrolled(omar, 'MATH101').
enrolled(shayan, 'CS305').
enrolled(shayan, 'CS310').
enrolled(usama, 'CS101').
enrolled(usama, 'MATH101').
enrolled(zara, 'CS201').
teaches(dr_ahmed, 'CS101').
teaches(dr_ahmed, 'CS102').
teaches(dr_bilal, 'MATH101').
teaches(dr_bilal, 'MATH201').
teaches(dr_bilal, 'MATH301').
teaches(dr_fatima, 'CS201').
teaches(dr_fatima, 'CS305').
teaches(dr_fatima, 'CS320').
teaches(dr_maryam, 'AI303').
teaches(dr_maryam, 'AI305').
teaches(dr_sara, 'AI301').
teaches(dr_sara, 'AI302').
teaches(dr_sara, 'AI401').
teaches(dr_usman, 'CS202').
teaches(dr_usman, 'CS310').
prerequisite('AI301', 'CS201').
prerequisite('AI301', 'MATH201').
prerequisite('AI302', 'AI301').
prerequisite('AI303', 'AI301').
prerequisite('AI305', 'MATH201').
prerequisite('AI401', 'AI301').
prerequisite('CS102', 'CS101').
prerequisite('CS201', 'CS102').
prerequisite('CS202', 'CS102').
prerequisite('CS305', 'CS102').
prerequisite('CS310', 'CS201').
prerequisite('CS320', 'CS102').
prerequisite('MATH201', 'MATH101').
prerequisite('MATH301', 'MATH101').

/* ---------------- R2: missing prerequisites ---------------- */
missing_prereqs(S, C, Missing) :-
    findall(P, (prerequisite(C, P), \+ completed(S, P)), Missing).

/* ---------------- R1: eligibility ---------------- */
eligible(S, C) :-
    course(C, _, _, _),
    missing_prereqs(S, C, []),
    \+ completed(S, C),
    \+ enrolled(S, C).

/* ---------------- R3 / R4: instructor <-> student ---------------- */
instructor_of(S, I) :- enrolled(S, C), teaches(I, C).
student_of(I, S) :- teaches(I, C), enrolled(S, C).

/* ---------------- R5: transitive prerequisites ---------------- */
all_prereqs(C, P) :- prerequisite(C, P).
all_prereqs(C, P) :- prerequisite(C, X), all_prereqs(X, P).

/* ---------------- R6: recommendations ---------------- */
recommended(S, C) :- eligible(S, C).

/* ---------------- R7: classmates ---------------- */
classmates(S1, S2) :- enrolled(S1, C), enrolled(S2, C), S1 \= S2.

/* ---------------- Contradiction helper ---------------- */
enrolled_without_prereq(S, C) :-
    enrolled(S, C), prerequisite(C, P), \+ completed(S, P).
