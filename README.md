# Airline booking system
_Submitted in fulfilment of a university assignment. Some details are omitted to deter future students._

See **guide.pdf** for an walkthrough of the application.

## Task
Develop a Web application implementing an online flight booking system.

### Requirements
- Five flight routes with real calendar dates
- Account for timezone differences
- Convenient search feature
- Booking and cancelling scheduled flights
- Prevent booking full flights
- Unique booking references
- Invoice page
- Visually appealing presentation

### Additional features
- Landing page with banner & featured destinations
- Search:
    - Round-trip option
    - Dynamic destinations
    - Searchable from/to select inputs
    - Depart/return calendar marked by availability, automatic next selection
    - Incomplete booking call to action
- Flight selection:
    - Weekly availability with validated navigation
    - Dynamic prices based on demand and remaining days
    - Overnight flights
- Route maps
- User session management
- Thorough validation throughout

## Instructions
Pull the image from GHCR and run the server (e.g. on port 8001):
```shell
docker pull ghcr.io/jarrowsm/flightapp:latest
docker run -it -p 8001:8000 ghcr.io/jarrowsm/flightapp:latest
```

## Stack
- django 5.1.9
- bootstrap 5.3.6
- bootstrap-icons 1.13.1
- choices.js 11.1.0
- flatpickr 4.6.13
- vanilla JS (ES2024)
- CSS3
