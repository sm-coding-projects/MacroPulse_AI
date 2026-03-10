---
name: project-conventions
description: Coding conventions, patterns, and style rules for MacroPulse AI. Use this skill when writing any code for the project to ensure consistency across backend and frontend. Covers error handling patterns, API response shapes, component patterns, and naming conventions.
---

# MacroPulse AI — Project Conventions

## Python Backend Conventions

### File Organization
- One router per file, one service per file
- Models in `models/schemas.py` (single file for v1)
- Prompts in `prompts/analysis.py` (single file for v1)
- Database setup isolated in `database.py`
- Config via Pydantic Settings in `config.py`

### Error Handling Pattern
Every service function follows this pattern:
```python
import logging

logger = logging.getLogger(__name__)

def fetch_something() -> SomeModel:
    """Fetch something from external API.
    
    Returns:
        SomeModel with the fetched data.
    
    Raises:
        ConnectionError: If the API is unreachable.
        ValueError: If the response is malformed.
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.Timeout:
        logger.error("Request to %s timed out", url)
        raise ConnectionError("The data source is not responding. Please try again later.")
    except requests.HTTPError as e:
        logger.error("HTTP %d from %s", e.response.status_code, url)
        raise ConnectionError(f"Data source returned an error (HTTP {e.response.status_code}).")
    
    try:
        data = response.json()
        return parse_data(data)
    except (KeyError, TypeError, json.JSONDecodeError) as e:
        logger.error("Failed to parse response: %s", e)
        raise ValueError("The data received was in an unexpected format.")
```

### API Response Pattern
All endpoints return consistent shapes:
```python
# Success
{"data": {...}, "error": null}

# Error
{"data": null, "error": "Human-readable error message"}
```

Never return raw exception messages. Write error messages as if explaining to a non-technical user.

### Import Order
```python
# 1. Standard library
import json
import logging
from datetime import datetime

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import pandas as pd

# 3. Local
from app.config import settings
from app.models.schemas import CapExData
```

### Naming
- Functions: `snake_case`, verbs for actions (`fetch_data`, `process_response`)
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private functions: prefix with `_`
- Pydantic models: descriptive nouns (`CapExQuarter`, `AnalyzeRequest`)

## TypeScript Frontend Conventions

### Component Pattern
```typescript
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { SomeType } from "@/lib/types";

interface ComponentProps {
  data: SomeType;
  isLoading?: boolean;
  className?: string;
}

export function Component({ data, isLoading = false, className }: ComponentProps) {
  const [state, setState] = useState<string>("");

  if (isLoading) {
    return <ShimmerLoader className={className} />;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn("rounded-xl bg-slate-900 border border-slate-800 p-6", className)}
    >
      {/* content */}
    </motion.div>
  );
}
```

### Hook Pattern
```typescript
"use client";

import { useState, useEffect, useCallback } from "react";

interface UseFeatureReturn {
  data: DataType | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useFeature(): UseFeatureReturn {
  const [data, setData] = useState<DataType | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchData();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { data, isLoading, error, refresh };
}
```

### Import Order
```typescript
// 1. React/Next.js
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

// 2. Third-party
import { motion, AnimatePresence } from "framer-motion";
import { LineChart, Line } from "recharts";
import { Settings, BarChart3 } from "lucide-react";

// 3. Local components
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

// 4. Local utilities and types
import { cn, formatCurrency } from "@/lib/utils";
import type { CapExData } from "@/lib/types";
```

### Naming
- Components: `PascalCase` (file and export match)
- Hooks: `camelCase` with `use` prefix
- Utility functions: `camelCase`
- Types/Interfaces: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Props interfaces: `{ComponentName}Props`
- CSS: Tailwind utility classes only — no custom CSS except globals.css

### Animation Defaults
```typescript
// Standard entrance animation
const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3 },
};

// Stagger children by 100ms
const staggerDelay = (index: number) => ({
  ...fadeInUp,
  transition: { ...fadeInUp.transition, delay: index * 0.1 },
});
```

### localStorage Keys
All localStorage keys are namespaced with `macropulse_`:
- `macropulse_llm_settings` — LLM configuration object

### Path Aliases
Use `@/` alias configured in tsconfig.json:
- `@/components/` → `src/components/`
- `@/lib/` → `src/lib/`
- `@/hooks/` → `src/hooks/`
