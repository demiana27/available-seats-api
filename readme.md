# Problem understanding

The goal of this project is to build a simple seat reservation API for a workshop with a fixed capacity of five seats.

The API provides three endpoints:
GET /status: Returns the current reservation status and the number of remaining seats.
POST /reservations: Reserves a seat for a user if the user has not already reserved one and a seat is available.
DELETE /reservations/{user_id}: Cancels an existing reservation and releases the seat (the quantity seats i need ).

The reservation data is stored in memory, so it is reset when the application restarts. The main challenge is ensuring that concurrent requests do not reserve more seats than are available.

## Assumptions

1. The workshop has a fixed capacity of five seats.
2. A user can reserve multiple seats in a single reservation, but cannot create more than one active reservation.
3. Each reservation is identified by a unique, non-empty `user_id`.
4. A user can cancel part or all of their existing reservation, as long as the cancellation quantity does not exceed the number of seats reserved.
5. Reservation data is stored in memory and is not persistent across application restarts.
6. The API does not require authentication or a database for this version.

## Invariants

The total number of reserved seats must never exceed the workshop capacity of five.

Each user can have at most one active reservation.

The number of remaining seats must equal the total capacity minus the sum of all reserved quantities.

The number of remaining seats must always be between zero and five.

A cancellation must not release more seats than the user has reserved.

Reservation and cancellation updates must preserve these invariants even when requests arrive concurrently.

## How to run the project

In PowerShell, after installing the dependencies from `requirements.txt`, run:

```bash
python -m uvicorn main:app --reload
```

Then, please go to `test.txt` to see how I tested the process.

to check there is race condition i run --> python concurrency_test.py and aslo after the lock to check that is solved

## Design decisions

`pescode -> python without API -> with HTTP API -> add a file to check for problems -> add a lock to prevent race conditions during reservation updates`

## Testing

The tests are in `test.txt`.

## Debugging investigation

## Concurrency reasoning

To speed up the process while keeping the system safe, I used a lock to avoid race conditions when multiple requests try to reserve or release seats at the same time.

## Tool/framework understanding

i used FastAPI maps HTTP methods and paths to Python functions. Pydantic models help validate the request body, while `HTTPException` allows the application to return an appropriate HTTP error response.
also I used Python's `threading.Lock` to protect reservation updates from concurrent execution. The critical section contains operations that read and modify shared reservation state,the  lock helps prevent two threads from simultaneously executing the protected section. However, every operation that needs coordinated access to the shared state must follow the same locking strategy.

## Learning notes

Concept  Meaning                         Example
Program  مجموعة تعليمات مكتوبة في كود  main.py
Process  نسخة من البرنامج وهي شغالة    Python server running
Thread  مسار تنفيذ داخل الـprocess     Thread handles a request
Task  شغل عايزين ننجزه                 Reserve a seat

## AI / external resources used

- ChatGPT:
i used to know how i test the race condtion and to understand why he write every line because to be honest i didn't know how to test it and aslo to check my sloution aslo make me remember about invoke .... to test the code in terminal also to make sure that i completly understand the concerncy and race condition
also he tell me that the diractory is better than the list in seats but i didn't think that because i can't add the one user twice it depend on quantity  
ans also to rewrite some paragraphs to make it more professional
- [YouTube playlist: Python FastAPI concurrency and seat reservations](https://www.youtube.com/watch?v=yvyKtJVVIdk&list=PLGbzY-VLUfcpzhB-iyGvju-NMMez_NNP9)
- [YouTube video: FastAPI tutorial](https://www.youtube.com/watch?v=uckj0Fwm0us)
- [YouTube video: Concurrency and parallelism in Python](https://www.youtube.com/watch?v=Zs-mBb6we_U)

## NOTE

The requirement is that a user can reserve more than one seat in a single booking when needed, not only one seat at a time. For example, a user may reserve 2 seats for themselves and a friend. The API therefore supports reservations by quantity, while still enforcing the rule that each user can have only one active reservation at any time, in line with the assessment requirements.

==============================================================
# Available Seats API — Testing and Debugging Notes

## 1. Testing Setup

I had difficulty testing HTTP requests with my usual setup on my laptop, so I used ChatGPT guidance to help me execute and test requests through the PowerShell terminal against my local FastAPI application.

This allowed me to test the API endpoints directly and observe the actual HTTP responses and changes to the reservation state.

I first tested the API without concurrency, then ran a concurrent reservation experiment to investigate a possible race condition.

## 2. Sequential Testing — Without Concurrency

The initial capacity was 5 seats.

### Test 1: Check Initial Availability

**Request:** `GET /status`

**Actual result:**
- Remaining seats: 5
- Reservations: Empty

**Conclusion:** The initial state was correct.

### Test 2: Reserve Seats

**Request:** Customer A101 requested 3 seats.

**Actual result:**
- Reservation succeeded.
- Remaining seats: 2.

**Conclusion:** The API successfully created the reservation and updated the available seat count.

### Test 3: Cancel Part of a Reservation

**Request:** A101 cancelled 2 seats.

**Actual result:**
- Cancellation succeeded.
- Remaining seats: 4.
- A101 still had 1 reserved seat.

I then called `GET /status` to verify the stored state.

**Conclusion:** The reservation quantity and remaining seat count were updated correctly.

### Test 4: Prevent Duplicate Reservations

**Request:** A101 attempted to create another reservation while already having a reservation.

**Actual result:**

```json
{
  "detail": "You have already reserved seats."
}
```

**Conclusion:** The duplicate-reservation validation worked as expected.

### Test 5: Reserve Seats for Another User

**Request:** A102 requested 3 seats.

**Actual result:**

- Reservation succeeded.
- Remaining seats: 1.

**Conclusion:** Another user could reserve seats when sufficient capacity was available.

### Test 6: Reject a Reservation Exceeding Availability

**Request:** A104 requested 3 seats when only 1 seat remained.

**Actual result:**

```json
{
  "detail": "Not enough seats available. Reservation rejected."
}
```

**Conclusion:** The API correctly rejected the request because the requested quantity exceeded the available capacity.

## 3. Concurrent Testing — Investigating a Race Condition

I used a Python concurrency test with `ThreadPoolExecutor` to submit two reservation requests concurrently.

The test first reserved 4 of the 5 seats for `SetupUser`, leaving only 1 seat available. Two additional customers then attempted to reserve 1 seat each.

### Before Adding a Lock

**Actual results:**

- SetupUser reserved 4 seats successfully.
- Customer A received HTTP 200 and was told the reservation succeeded.
- Customer B received HTTP 200 and was also told the reservation succeeded.
- The final state contained 6 reserved seats despite a capacity of 5.
- The API reported `remaining_seats = -1`.

**Evidence:**

```text
Customer A: status 200
Customer B: status 200

Final status:
remaining_seats: -1
reservations:
    SetupUser: 4
    CustomerB: 1
    CustomerA: 1
```

**Initial hypotheses:**

- The available-seat check and reservation update might not be protected as one operation.
- Both requests might check availability before either request saves its reservation.
- The shared reservation state might be updated based on stale availability.

### Root Cause

The availability check and reservation update were not protected by a shared lock. This allowed both concurrent requests to be accepted based on the same available seat.

The problem was not the subtraction itself. The problem was that both requests could make their reservation decisions before accounting for the other request.

### Fix

I introduced a shared `threading.Lock` and protected the critical section containing the duplicate-user check, availability calculation, capacity validation, and reservation update.

The lock ensures that only one request at a time can execute this protected section within the same Python process.

### After Adding the Lock

**Actual results:**

- SetupUser reserved 4 seats successfully.
- One customer successfully reserved the remaining seat.
- The other customer received HTTP 400 with the message `Not enough seats available. Reservation rejected.`
- The final state contained 5 reserved seats.
- The API reported `remaining_seats = 0`.

**Evidence:**

```text
Setup: status 200, remaining_seats = 1
Customer A: status 400, insufficient seats
Customer B: status 200, remaining_seats = 0

Final status:
remaining_seats: 0
reservations:
    SetupUser: 4
    CustomerB: 1
```

**Verification:** The same concurrency experiment was run after adding the lock. The observed result showed that the capacity was no longer exceeded in this test.

## 4. Lessons Learned

- Sequential tests verify the API's basic business rules.
- Concurrent tests help reveal timing-dependent bugs that may not appear in ordinary sequential tests.
- A race condition can occur when multiple requests read shared state and make decisions before the state is updated.
- A lock protects the critical section when requests share the same process and lock instance.
- A production solution using multiple worker processes or multiple servers needs an appropriate database transaction or atomic operation; an in-memory Python lock alone is not sufficient.
