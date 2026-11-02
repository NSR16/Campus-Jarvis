# Campus Brain Retrieval Evaluation

Date: 2026-10-02

## Scope and Corpus

This evaluation called the existing `retrieve_chunks(question, pool, top_k=5)` directly for all 20 questions, against the configured PostgreSQL/pgvector database and Ollama embedding service. All 20 calls returned five chunks. No production code, routes, retrieval SQL, or schema were changed.

Before expanding the corpus, the database contained 6 document rows/chunks. Twelve unique, explicitly labeled `evaluation_sample` documents were added through the existing ingestion service. The verified corpus now has 18 document rows, 18 chunks, and 17 distinct chunk contents. One exact duplicate pair pre-existed: chunk IDs 4 and 5 are identical copies of the Campus Coding Workshop Announcement from `Student Technical Club`. They were preserved rather than deleted. The 12 added evaluation documents are synthetic samples, not verified facts about a real campus; their stored contents are prefixed `EVALUATION SAMPLE ?`.

The corpus also contains one chunk for each document. The references below give the exact stored content. In the result ledger, every `cN` maps to the source/document and full retrieved text in this catalog; the `R`/`I` judgment is based on whether that text supports a requested answer fact, not its distance. For partially answerable questions, `R` means the text supports at least one requested component. For unanswerable questions, a chunk can be topically related but is `I` if it does not support the requested fact.

## Stored Chunk Catalog

| Chunk | Document / source | Retrieved content |
|---|---|---|
| c1 | Library hours / `manual-verification-library-hours.txt` | The campus library is open Monday through Friday from 9 AM to 5 PM. It is closed on public holidays. |
| c2 | Campus Canteen Hours / `manual-test-canteen-hours.txt` | The campus canteen operates from 8 AM to 8 PM daily. Breakfast is served from 8 AM to 10 AM. |
| c3 | Semester Examination Notice / `manual-test-exam-notice.txt` | Semester examinations begin on November 10. Students must carry their college ID cards to the examination hall. |
| c4 | Campus Coding Workshop Announcement / `Student Technical Club` | CAMPUS CODING WORKSHOP — STUDENT ANNOUNCEMENT The Student Technical Club is organizing a coding workshop for undergraduate students on October 5, 2026. The workshop will begin at 10:00 AM and conclude at 1:00 PM. It will be conducted in Computer Lab 2, Academic Block. The session will cover Python programming fundamentals, problem-solving techniques, and an introduction to competitive programming. Students from all branches are welcome to participate. Participants should bring their college ID cards and laptops. Registration closes on October 3, 2026. Students can register through the Student Technical Club office. Issued by: Student Technical Club |
| c5 | Campus Coding Workshop Announcement / `Student Technical Club` | CAMPUS CODING WORKSHOP — STUDENT ANNOUNCEMENT The Student Technical Club is organizing a coding workshop for undergraduate students on October 5, 2026. The workshop will begin at 10:00 AM and conclude at 1:00 PM. It will be conducted in Computer Lab 2, Academic Block. The session will cover Python programming fundamentals, problem-solving techniques, and an introduction to competitive programming. Students from all branches are welcome to participate. Participants should bring their college ID cards and laptops. Registration closes on October 3, 2026. Students can register through the Student Technical Club office. Issued by: Student Technical Club |
| c6 | Campus Sports Facilities and Timings / `Campus Sports Committee` | CAMPUS SPORTS FACILITIES — STUDENT NOTICE The campus sports complex is open to students from Monday to Saturday, 6:00 AM to 8:00 PM. It remains closed on Sundays. The basketball court is available from 7:00 AM to 6:00 PM. The badminton courts can be used from 8:00 AM to 7:00 PM. Students must carry their valid college ID cards to access the sports facilities. Sports equipment can be borrowed from the sports office by submitting a valid student ID. Equipment must be returned on the same day. Students are advised to wear appropriate sports clothing and footwear while using the facilities. Issued by: Campus Sports Committee |
| c7 | Evaluation Sample: Fall 2026 Academic Calendar / `eval-sample-academic-calendar-2026.txt` | EVALUATION SAMPLE ? Fall 2026 Academic Calendar. Fall classes begin August 24, 2026. The add/drop period closes August 31. Midterm examinations run October 12 through October 16. Final examinations begin November 10 and continue through November 20. The semester ends December 18, 2026. |
| c8 | Evaluation Sample: Residence Hall Notice / `eval-sample-residence-hall.txt` | EVALUATION SAMPLE ? Residence Hall Notice. Residence hall front desks are staffed daily from 6:00 AM until midnight. Quiet hours run from 10:00 PM to 6:00 AM. Resident guests must sign in at the front desk and may visit between 4:00 PM and 9:00 PM. Overnight guests require approval from the resident adviser at least one day in advance. |
| c9 | Evaluation Sample: Campus Shuttle Schedule / `eval-sample-shuttle-schedule.txt` | EVALUATION SAMPLE ? Campus Shuttle Schedule. The campus shuttle runs from the Main Gate through Academic Block to North Residence every 20 minutes from 7:00 AM to 10:00 AM on weekdays. Afternoon service runs from 3:30 PM to 8:00 PM on the same route. The last weekday shuttle leaves the Main Gate at 8:00 PM. Shuttle service does not operate on Sundays. |
| c10 | Evaluation Sample: Merit Scholarship Guide / `eval-sample-merit-scholarship.txt` | EVALUATION SAMPLE ? Merit Scholarship Guide. Full-time undergraduate students with a cumulative GPA of at least 3.5 may apply for the merit scholarship. Applications must be submitted through the student portal by September 30, 2026. Applicants must provide a current transcript and a faculty recommendation. Scholarship decisions are scheduled for October 15. |
| c11 | Evaluation Sample: Course Attendance Policy / `eval-sample-attendance-policy.txt` | EVALUATION SAMPLE ? Course Attendance Policy. Students are expected to attend at least 75 percent of the scheduled sessions in each course. A student who falls below the minimum may be barred from the final examination. Requests to excuse an absence should be submitted to the department office within three working days and include supporting documentation. |
| c12 | Evaluation Sample: Career Placement Fair / `eval-sample-placement-fair.txt` | EVALUATION SAMPLE ? Career Placement Fair. The campus career fair will be held October 20, 2026, from 10:00 AM to 3:00 PM in the Student Center ballroom. The fair is open to final-year undergraduate students. Students must upload a resume to the career portal by October 15 to receive an employer meeting schedule. Walk-in registration is not available. |
| c13 | Evaluation Sample: Tuition Payment Deadlines / `eval-sample-tuition-deadlines.txt` | EVALUATION SAMPLE ? Tuition Payment Deadlines. The Fall 2026 tuition installment is due September 15, 2026. A late payment charge is applied beginning September 22. Payments can be made through the student portal or at the campus cashier during weekday business hours. Housing charges are billed separately and are due September 10. |
| c14 | Evaluation Sample: Student Advising Services / `eval-sample-advising-services.txt` | EVALUATION SAMPLE ? Student Advising Services. The Student Advising Center helps with course selection, degree planning, and academic support referrals. Advisers meet students Monday through Friday from 9:00 AM to 4:00 PM. Appointments can be booked through the student portal. Same-day walk-in appointments are offered from 1:00 PM to 2:00 PM when an adviser is available. |
| c15 | Evaluation Sample: Campus Health Center / `eval-sample-health-center.txt` | EVALUATION SAMPLE ? Campus Health Center. The Campus Health Center provides basic first aid and nurse consultations to enrolled students. It is open Monday through Friday from 8:00 AM to 5:00 PM and is located beside the Student Services Building. Students should bring their campus identification card. The center is closed on weekends and official campus holidays. |
| c16 | Evaluation Sample: Student Clubs Directory / `eval-sample-student-clubs.txt` | EVALUATION SAMPLE ? Student Clubs Directory. The Robotics Club meets Thursdays at 5:00 PM in Engineering Lab 3. The Eco Club meets on the first Tuesday of each month at 4:00 PM in the campus garden. New members may register at the Student Activities Office during weekday hours. The clubs fair will take place September 2, 2026, on the central quad. |
| c17 | Evaluation Sample: Founders Day Holiday Notice / `eval-sample-founders-day-holiday.txt` | EVALUATION SAMPLE ? Founders Day Holiday Notice. The campus will observe Founders Day on Friday, October 2, 2026. Classes and administrative offices will be closed for the day. The library and residence halls will remain open according to their regular schedules. Normal classes resume on Monday, October 5. |
| c18 | Evaluation Sample: Computer Lab Access and Printing / `eval-sample-computer-lab-services.txt` | EVALUATION SAMPLE ? Computer Lab Access and Printing. The general-use computer lab in the Learning Commons is open Monday through Friday from 7:00 AM to 10:00 PM. Students must sign in with their campus ID. Printing is available from lab computers using a prepaid print account. Lab assistants are present from 9:00 AM to 6:00 PM on weekdays; printing remains available outside staffed hours. |

## Questions and Expected Evidence

| Q | Category | Question | Expected evidence |
|---|---|---|---|
| 1 | Direct | What time does the campus library open and close Monday through Friday? | c1 |
| 2 | Direct | What hours is breakfast served at the campus canteen? | c2 |
| 3 | Direct | What minimum attendance percentage is required in each course? | c11 |
| 4 | Direct | What must students carry to use the sports facilities? | c6 |
| 5 | Paraphrased | Where can I get help planning my classes and degree? | c14 |
| 6 | Paraphrased | At what time does the last weekday shuttle depart from the Main Gate? | c9 |
| 7 | Paraphrased | What supporting materials must an undergraduate submit for the merit award application? | c10 |
| 8 | Cross-document | Compare the weekday operating hours of the library and the Campus Health Center. | c1, c15 |
| 9 | Cross-document | Which deadline comes first: the merit scholarship application or coding workshop registration? | c10, c4/c5 (one unique workshop content) |
| 10 | Cross-document | Compare the days and hours when the library and sports complex are open. | c1, c6 |
| 11 | Partially answerable | What is the coding workshop date, venue, and registration fee? | c4/c5 supports date and venue; fee is absent |
| 12 | Partially answerable | What are the sports complex hours and the swimming pool hours? | c6 supports complex hours; pool information is absent |
| 13 | Partially answerable | What are the Campus Health Center hours and its telephone number? | c15 supports hours; telephone number is absent |
| 14 | Unanswerable campus-related | What is the campus Wi-Fi password? | None |
| 15 | Unanswerable campus-related | How much does the campus shuttle charge for a ride? | None; c9 describes schedule, not fare |
| 16 | Unanswerable campus-related | How much money does the merit scholarship award? | None; c10 describes eligibility/deadline, not amount |
| 17 | Unanswerable campus-related | Where can a student collect a replacement campus ID card? | None; c3/c6/c15 mention IDs but not replacement service/location |
| 18 | Clearly unrelated | What is the current weather in Paris? | None |
| 19 | Clearly unrelated | Who won the 2026 FIFA World Cup? | None |
| 20 | Clearly unrelated | How do I bake a sourdough loaf? | None |

## Ranked Retrieval Results

Each entry is `rank: chunk @ cosine distance [content relevance]`. Source/document and full text for each chunk ID are in the Stored Chunk Catalog. All scores are actual results from `retrieve_chunks(..., top_k=5)`.

| Q | Rank 1 | Rank 2 | Rank 3 | Rank 4 | Rank 5 |
|---|---|---|---|---|---|
| 1 | 1: c1 @ 0.084483 [R] | 2: c2 @ 0.331800 [I] | 3: c17 @ 0.338619 [I] | 4: c6 @ 0.352070 [I] | 5: c18 @ 0.358209 [I] |
| 2 | 1: c2 @ 0.083541 [R] | 2: c6 @ 0.352533 [I] | 3: c1 @ 0.356073 [I] | 4: c15 @ 0.362495 [I] | 5: c9 @ 0.376130 [I] |
| 3 | 1: c11 @ 0.257304 [R] | 2: c9 @ 0.401609 [I] | 3: c7 @ 0.401632 [I] | 4: c16 @ 0.405127 [I] | 5: c8 @ 0.408882 [I] |
| 4 | 1: c6 @ 0.183866 [R] | 2: c3 @ 0.358095 [I] | 3: c15 @ 0.384609 [I] | 4: c18 @ 0.438188 [I] | 5: c11 @ 0.438350 [I] |
| 5 | 1: c14 @ 0.349668 [R] | 2: c12 @ 0.407968 [I] | 3: c15 @ 0.416978 [I] | 4: c3 @ 0.420205 [I] | 5: c4 @ 0.420695 [I] |
| 6 | 1: c9 @ 0.287231 [R] | 2: c17 @ 0.419702 [I] | 3: c1 @ 0.433177 [I] | 4: c2 @ 0.439885 [I] | 5: c8 @ 0.469847 [I] |
| 7 | 1: c10 @ 0.223689 [R] | 2: c14 @ 0.442370 [I] | 3: c12 @ 0.446929 [I] | 4: c11 @ 0.448470 [I] | 5: c6 @ 0.458135 [I] |
| 8 | 1: c15 @ 0.254451 [R] | 2: c1 @ 0.255933 [R] | 3: c18 @ 0.329491 [I] | 4: c2 @ 0.331302 [I] | 5: c9 @ 0.337781 [I] |
| 9 | 1: c10 @ 0.273843 [R] | 2: c5 @ 0.310723 [R] | 3: c4 @ 0.310723 [R] | 4: c12 @ 0.358015 [I] | 5: c16 @ 0.380725 [I] |
| 10 | 1: c1 @ 0.224399 [R] | 2: c6 @ 0.282224 [R] | 3: c18 @ 0.311317 [I] | 4: c17 @ 0.347731 [I] | 5: c9 @ 0.349083 [I] |
| 11 | 1: c4 @ 0.276828 [R] | 2: c5 @ 0.276828 [R] | 3: c16 @ 0.394912 [I] | 4: c12 @ 0.395520 [I] | 5: c18 @ 0.428312 [I] |
| 12 | 1: c6 @ 0.325330 [R] | 2: c2 @ 0.409782 [I] | 3: c1 @ 0.456444 [I] | 4: c9 @ 0.459136 [I] | 5: c16 @ 0.464536 [I] |
| 13 | 1: c15 @ 0.240760 [R] | 2: c6 @ 0.361731 [I] | 3: c2 @ 0.380472 [I] | 4: c1 @ 0.402412 [I] | 5: c8 @ 0.408395 [I] |
| 14 | 1: c15 @ 0.395983 [I] | 2: c6 @ 0.397101 [I] | 3: c4 @ 0.423464 [I] | 4: c5 @ 0.423464 [I] | 5: c3 @ 0.434495 [I] |
| 15 | 1: c9 @ 0.275245 [I] | 2: c13 @ 0.431424 [I] | 3: c15 @ 0.460257 [I] | 4: c6 @ 0.478559 [I] | 5: c16 @ 0.479963 [I] |
| 16 | 1: c10 @ 0.267792 [I] | 2: c13 @ 0.484248 [I] | 3: c7 @ 0.535075 [I] | 4: c12 @ 0.546522 [I] | 5: c14 @ 0.550436 [I] |
| 17 | 1: c3 @ 0.321383 [I] | 2: c6 @ 0.330461 [I] | 3: c15 @ 0.352605 [I] | 4: c18 @ 0.422678 [I] | 5: c16 @ 0.456626 [I] |
| 18 | 1: c16 @ 0.510995 [I] | 2: c7 @ 0.512743 [I] | 3: c12 @ 0.514762 [I] | 4: c8 @ 0.538104 [I] | 5: c13 @ 0.549222 [I] |
| 19 | 1: c7 @ 0.512669 [I] | 2: c12 @ 0.578543 [I] | 3: c10 @ 0.589253 [I] | 4: c17 @ 0.592134 [I] | 5: c16 @ 0.598433 [I] |
| 20 | 1: c5 @ 0.547481 [I] | 2: c4 @ 0.547481 [I] | 3: c10 @ 0.572646 [I] | 4: c12 @ 0.583645 [I] | 5: c2 @ 0.588349 [I] |

## Analysis

Relevance is judged against expected evidence, not similarity alone. There are 18 relevant result instances and 82 irrelevant result instances among the 100 retrieved slots. Because chunks c4 and c5 are an exact duplicate, recall is also reported after treating them as one unique evidence item. The 13 answerable/partially answerable questions have 16 unique question-evidence pairs.

- **Recall@1 (unique evidence): 13/16 = 81.25%.** Strict complete-evidence coverage is 10/13 questions (76.9%) because Q8, Q9, and Q10 each require two distinct evidence chunks; each has one at rank 1 and the other within rank 2 or 3. Every answerable question has at least one relevant result at rank 1.
- **Recall@3 (unique evidence): 16/16 = 100%.** Complete-evidence coverage is 13/13 questions.
- **Recall@5 (unique evidence): 16/16 = 100%.** Complete-evidence coverage remains 13/13. Physical chunk-row recall at rank 1 is 13/18 because the two copies of the workshop chunk count as separate rows; deduplicating identical text gives 13/16.
- Relevant result-instance distances: **0.083541–0.349668**. Irrelevant result-instance distances: **0.267792–0.598433**. They overlap materially from **0.267792–0.349668**, so there is no clean separating threshold.
- Distance histogram (lower bound inclusive, upper bound exclusive):

| Distance range | Relevant results | Irrelevant results |
|---|---:|---:|
| [0.00, 0.20) | 3 | 0 |
| [0.20, 0.25) | 3 | 0 |
| [0.25, 0.30) | 8 | 2 |
| [0.30, 0.35) | 4 | 10 |
| [0.35, 0.40) | 0 | 17 |
| [0.40, 0.50) | 0 | 35 |
| [0.50, 1.00] | 0 | 18 |

- All 4 unanswerable campus questions and all 3 unrelated questions returned five chunks. At a candidate cutoff of 0.349668, top-1 results pass for **3/4** unanswerable campus questions (shuttle fare, scholarship amount, and replacement ID location) and **0/3** unrelated questions. The first two have very close but answer-unsupported subject matter; a distance cutoff does not establish answerability.
- Duplicate behavior: c4 and c5 are identical and both appear in Q9, Q11, Q14, and Q20, using two of five result positions each time. Other than that exact pre-existing pair, there are 17 distinct chunk contents. `top_k=5` returns 5/18 rows per query. Since all unique expected evidence is recovered by top 3, top_k=5 is reasonable for this small corpus, although the duplicate consumes result diversity.

### Empirical Cutoff Scenarios

These are observed cutoffs for analysis, not recommended production thresholds. Counts use all 100 returned result instances; `relevant lost` and `irrelevant retained` identify errors the cutoff would introduce. The boundary values were chosen from the observed distance distribution, not rounded heuristics.

| Candidate cutoff (distance <=) | Relevant retained | Relevant incorrectly discarded | Irrelevant filtered | Irrelevant incorrectly retained |
|---:|---:|---:|---:|---:|
| 0.267791 (just below nearest irrelevant at 0.267792) | 9/18 | 9 | 82/82 | 0 |
| 0.310723 (observed relevant workshop distance) | 16/18 | 2 (Q5 advising c14; Q12 sports c6) | 80/82 | 2 (Q15 shuttle fare c9; Q16 scholarship amount c10) |
| 0.349668 (farthest relevant result) | 18/18 | 0 | 70/82 | 12 |

Even the middle candidate retains false positives for unanswerable questions while losing two relevant results. The last retains every relevant result in this sample but leaves 12 irrelevant results. Combined with the overlapping ranges, tiny synthetic corpus, and the duplicate chunk pair, this evaluation does **not** justify adopting a distance threshold.

## Recommendation

**D. Improve document deduplication/diversity first.** The exact duplicate workshop chunks demonstrably consume two of five results and crowd out distinct content. Do not add a threshold or change top_k based on this small evaluation: unique evidence recall is already complete by rank 3, while relevant/irrelevant distances overlap. Re-evaluate on a larger, representative, deduplicated corpus before changing retrieval behavior.
