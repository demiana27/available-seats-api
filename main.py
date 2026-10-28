from fastapi import FastAPI, HTTPException, Query
from httpcore import request
from pydantic import BaseModel
import time
from threading import Lock


reservation_lock = Lock()
app = FastAPI()

capacity = 5
reservations = {}


class ReservationRequest(BaseModel):
    user_id: str
    quantity: int


@app.get("/status")
def get_status():
    reserved_seats = sum(reservations.values())
    remaining_seats = capacity - reserved_seats
    return {"remaining_seats": remaining_seats, "reservations": reservations}


@app.post("/reservations")
def reserve_seats(request: ReservationRequest):
    with reservation_lock:
        if request.user_id in reservations:
            raise HTTPException(
                status_code=409,
                detail="You have already reserved seats."
            )
        if request.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid quantity. Reservation rejected."
            )

        available_seats = capacity - sum(reservations.values())
        ##time.sleep(2)  # TEMPORARY: testing only
    
        if request.quantity > available_seats:
            raise HTTPException(
                status_code=400,
                detail="Not enough seats available. Reservation rejected."
            )

        reservations[request.user_id] = request.quantity
        return {
            "message": f"Reservation successful. {request.quantity} seats reserved for user {request.user_id}.",
            "remaining_seats": capacity - sum(reservations.values())
        }


@app.delete("/reservations/{user_id}")
def delete_reservation(user_id: str, quantity: int = Query(..., gt=0)):
    if user_id not in reservations:
        raise HTTPException(
            status_code=404,
            detail="No reservation found for this user. Cancellation rejected."
        )
    if quantity > reservations[user_id]:
        raise HTTPException(
            status_code=400,
            detail="Cancellation quantity exceeds reserved seats."
        )

    if quantity == reservations[user_id]:
        del reservations[user_id]
    else:
        reservations[user_id] -= quantity

    return {
        "message": f"Reservation for user {user_id} has been canceled.",
        "remaining_seats": capacity - sum(reservations.values())
    }