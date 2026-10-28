from concurrent.futures import ThreadPoolExecutor
import httpx

BASE_URL = "http://127.0.0.1:8000"


def reserve(user_id, quantity):
    response = httpx.post(
        f"{BASE_URL}/reservations",
        json={
            "user_id": user_id,
            "quantity": quantity
        },
        timeout=10
    )

    return {
        "user": user_id,
        "status": response.status_code,
        "result": response.json()
    }


# Start from a clean server state by restarting Uvicorn first.
# Reserve 4 of the 5 seats.
setup = reserve("SetupUser", 4)
print("Setup:", setup)

# Only one seat remains. Both users now request one seat.
with ThreadPoolExecutor(max_workers=2) as executor:
    future_a = executor.submit(reserve, "CustomerA", 1)
    future_b = executor.submit(reserve, "CustomerB", 1)

    print("Customer A:", future_a.result())
    print("Customer B:", future_b.result())

print("Final status:", httpx.get(f"{BASE_URL}/status").json())


##python concurrency_test.py 
#Setup: {'user': 'SetupUser', 'status': 200, 'result': {'message': 'Reservation successful. 4 seats reserved for user SetupUser.', 'remaining_seats': 1}}
#Customer A: {'user': 'CustomerA', 'status': 200, 'result': {'message': 'Reservation successful. 1 seats reserved for user CustomerA.', 'remaining_seats': -1}}
#Customer B: {'user': 'CustomerB', 'status': 200, 'result': {'message': 'Reservation successful. 1 seats reserved for user CustomerB.', 'remaining_seats': 0}}
#Final status: {'remaining_seats': -1, 'reservations': {'SetupUser': 4, 'CustomerB': 1, 'CustomerA': 1}}
#/