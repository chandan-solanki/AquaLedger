"""Business modules (auth, companies, fish, invoicing, ...).

Each module owns its own tables, service layer, and router, and follows the
same internal shape:

    modules/<name>/
        router.py       # FastAPI routes only - no business logic
        schemas.py      # Pydantic v2 request/response DTOs
        models.py       # SQLAlchemy ORM
        repository.py   # all queries; returns models, never DTOs
        service.py      # use-cases, orchestration, transactions
        domain.py        # entities, value objects, invariants (rich modules only)
        events.py        # domain events emitted
        tasks.py         # Celery tasks owned by this module
        exceptions.py
        constants.py

Rule: router.py may only call service.py. service.py may only call its own
repository.py plus other modules' service.py.
"""
