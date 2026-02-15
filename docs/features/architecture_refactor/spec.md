# Architectural Refactoring Specification

## 🚨 Problem Statement
The initial "Layered Architecture" (separating `agents`, `core/domain`, `core/repositories`) proved inefficient for scalability.
- **Low Cohesion:** Implementing a single feature required modifying files across 4-5 different directories.
- **Cognitive Load:** Difficult to see the full scope of a domain (e.g., Real Estate) at a glance.
- **Import Hell:** Growing complexity in import paths.

## 🎯 Goal
Transition to a **Domain-Driven Modular Architecture** (Modular Monolith) to improve cohesion and maintainability.

## 🏗️ Proposed Structure
```text
src/
├── common/             # Shared utilities & prompts (System Persona)
├── modules/            # Domain Modules
│   ├── finance/        # All Finance logic (Models, Repo, Service)
│   └── real_estate/    # All Real Estate logic
├── main.py             # Entrypoint wiring modules together
└── tests/              # Separate test directory (mirroring src structure)
```

## 📏 Principles
1. **Vertical Slicing:** Group code by feature/domain, not by technical layer.
2. **Encapsulation:** Modules should expose a `Service` (Agent) and keep repositories internal if possible.
3. **Explicit Dependencies:** Use relative imports within modules (`.models`, `.repository`).
