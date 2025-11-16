# MakeSlides Architecture

## Overview

MakeSlides is evolving into a hybrid platform with three tiers:
1. **CLI Tool** - Local processing for technical users
2. **API Backend** - FastAPI or Supabase Edge Functions
3. **Web UI** - Next.js frontend for visual editing

## Current Architecture (Phase 1 & 2) ✅

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Tools                                 │
├─────────────────────────────────────────────────────────────────┤
│  makeslides/                                                     │
│  ├── guide/                  # Parse facilitator guides          │
│  │   └── parser.py          # Claude AI → JSON                  │
│  ├── diagrams/               # Generate diagrams                │
│  │   └── renderer.py        # Mermaid → PNG/SVG                 │
│  ├── markdown/               # Format markdown                   │
│  │   └── generator.py       # JSON → Markdown                   │
│  ├── images/                 # Image management                  │
│  │   └── imgur_uploader.py  # Imgur API (permanent hosting)     │
│  ├── exporters/              # Multi-format export ⭐ NEW       │
│  │   ├── base.py            # Abstract base exporter            │
│  │   ├── pptx_exporter.py   # PowerPoint export                │
│  │   └── revealjs_exporter.py # reveal.js HTML export          │
│  └── slides/                 # Google Slides generation         │
│      └── builder.py          # md2gslides wrapper               │
│                                                                   │
│  scripts/                                                        │
│  ├── magicSlide.sh          # Workflow orchestrator             │
│  └── export_presentation.py # Unified export CLI ⭐ NEW         │
└─────────────────────────────────────────────────────────────────┘
```

### Export Formats Supported

| Format | Status | Dependencies | Use Case |
|--------|--------|--------------|----------|
| **PPTX** | ✅ Ready | python-pptx | Offline editing, corporate use |
| **reveal.js** | ✅ Ready | None (HTML/CSS/JS) | Web presentations, training |
| **Google Slides** | ✅ Existing | md2gslides, OAuth | Cloud collaboration |
| **PDF** | 🔜 Planned | reportlab | Handouts, printing |
| **Marp** | 🔜 Planned | marp-cli | Markdown-based slides |
| **Beamer** | 🔜 Planned | LaTeX | Academic presentations |

### Image Hosting

**Phase 1 Solution: Imgur API** ✅

```python
# Permanent, free hosting
from makeslides.images.imgur_uploader import upload_image

url = upload_image("images/diagram.png")
# Returns: https://i.imgur.com/xxxxx.png (permanent)
```

**Benefits**:
- ✅ Free tier is generous (unlimited anonymous uploads)
- ✅ Images don't expire (vs litterbox 24h)
- ✅ Reliable CDN
- ✅ Well-documented API
- ✅ No authentication needed for basic uploads

---

## Future Architecture (Phase 3-5) 🚀

### Supabase + Vercel Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Frontend (Vercel)                             │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Next.js 14 App (app/ directory)                               │  │
│  │  ├── app/                                                       │  │
│  │  │   ├── (auth)/          # Auth pages                        │  │
│  │  │   ├── dashboard/       # User dashboard                     │  │
│  │  │   ├── editor/          # Presentation editor               │  │
│  │  │   └── api/             # API routes (optional)             │  │
│  │  ├── components/                                               │  │
│  │  │   ├── editor/          # TipTap editor components          │  │
│  │  │   ├── preview/         # Live preview components           │  │
│  │  │   └── ui/              # shadcn/ui components              │  │
│  │  └── lib/                                                      │  │
│  │      ├── supabase/        # Supabase client                   │  │
│  │      └── stores/          # Zustand state management          │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌──────────────────────────────────────────────────────────────────────┐
│                   Backend (Supabase)                                  │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Supabase Services                                             │  │
│  │  ├── Database (PostgreSQL)                                    │  │
│  │  │   ├── presentations   # Store presentation metadata       │  │
│  │  │   ├── slides          # Individual slide data             │  │
│  │  │   ├── templates       # Reusable templates                │  │
│  │  │   └── collaborators   # User permissions                  │  │
│  │  ├── Storage (S3-compatible)                                  │  │
│  │  │   ├── images/         # User-uploaded images              │  │
│  │  │   ├── diagrams/       # Generated diagrams                │  │
│  │  │   └── exports/        # Generated presentations           │  │
│  │  ├── Auth                                                     │  │
│  │  │   ├── Email/Password                                       │  │
│  │  │   ├── OAuth (Google, GitHub)                              │  │
│  │  │   └── Row Level Security (RLS)                            │  │
│  │  ├── Edge Functions (Deno)                                    │  │
│  │  │   ├── parse-guide     # Claude AI guide parsing           │  │
│  │  │   ├── render-diagram  # Mermaid rendering                 │  │
│  │  │   ├── export-pptx     # PowerPoint export                 │  │
│  │  │   └── export-revealjs # reveal.js export                  │  │
│  │  └── Realtime                                                 │  │
│  │      ├── Presence        # Who's viewing/editing             │  │
│  │      ├── Broadcast       # Cursor positions                   │  │
│  │      └── Database Changes # Live updates                     │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌──────────────────────────────────────────────────────────────────────┐
│                   Python Processing Service                           │
│  (Optional - for heavy processing)                                   │
│  ├── FastAPI                                                          │
│  │   ├── /parse            # Guide parsing endpoint                  │
│  │   ├── /diagrams         # Diagram generation                      │
│  │   └── /export           # Multi-format export                     │
│  └── Deploy to: Railway, Render, or Supabase Edge Functions          │
└──────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Frontend (Vercel)

**Next.js 14** - React framework with App Router
```json
{
  "framework": "Next.js 14",
  "language": "TypeScript",
  "styling": "TailwindCSS",
  "components": "shadcn/ui",
  "editor": "TipTap (ProseMirror)",
  "state": "Zustand",
  "forms": "React Hook Form + Zod",
  "dnd": "@dnd-kit/core"
}
```

**Key Features**:
- Server-side rendering (SSR) for SEO
- Edge functions for global performance
- Automatic code splitting
- Image optimization
- Free hobby tier (generous)

#### Backend (Supabase)

**Supabase** - Open-source Firebase alternative
```json
{
  "database": "PostgreSQL 15+",
  "storage": "S3-compatible object storage",
  "auth": "GoTrue (JWT)",
  "realtime": "Phoenix Channels",
  "functions": "Deno Edge Functions"
}
```

**Why Supabase**:
- ✅ Generous free tier (500MB database, 1GB storage, 50MB file uploads)
- ✅ Real-time subscriptions built-in
- ✅ Row-level security (RLS) for data protection
- ✅ Auto-generated REST & GraphQL APIs
- ✅ Edge Functions (Deno) for serverless compute
- ✅ Can self-host if needed
- ✅ Scales to production

### Database Schema (PostgreSQL)

```sql
-- Presentations table
CREATE TABLE presentations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  source_guide TEXT, -- Original markdown
  slides_json JSONB NOT NULL,
  theme TEXT DEFAULT 'modern',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  published BOOLEAN DEFAULT FALSE,
  slug TEXT UNIQUE
);

-- Slides table (denormalized for easier editing)
CREATE TABLE slides (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  presentation_id UUID REFERENCES presentations(id) ON DELETE CASCADE,
  slide_number INTEGER NOT NULL,
  title TEXT,
  content TEXT,
  layout TEXT DEFAULT 'content',
  image_url TEXT,
  diagram_type TEXT,
  diagram_content TEXT,
  facilitator_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(presentation_id, slide_number)
);

-- Templates table
CREATE TABLE templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users,
  name TEXT NOT NULL,
  description TEXT,
  slides_json JSONB NOT NULL,
  category TEXT,
  is_public BOOLEAN DEFAULT FALSE,
  downloads INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Collaborators table
CREATE TABLE collaborators (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  presentation_id UUID REFERENCES presentations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'owner')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(presentation_id, user_id)
);

-- Comments table (for collaborative editing)
CREATE TABLE comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slide_id UUID REFERENCES slides(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users NOT NULL,
  content TEXT NOT NULL,
  resolved BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE presentations ENABLE ROW LEVEL SECURITY;
ALTER TABLE slides ENABLE ROW LEVEL SECURITY;
ALTER TABLE collaborators ENABLE ROW LEVEL SECURITY;
ALTER TABLE comments ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view own presentations"
  ON presentations FOR SELECT
  USING (auth.uid() = user_id OR id IN (
    SELECT presentation_id FROM collaborators WHERE user_id = auth.uid()
  ));

CREATE POLICY "Users can edit own presentations"
  ON presentations FOR UPDATE
  USING (auth.uid() = user_id OR id IN (
    SELECT presentation_id FROM collaborators
    WHERE user_id = auth.uid() AND role IN ('editor', 'owner')
  ));
```

### API Routes (Next.js + Supabase Edge Functions)

#### Next.js API Routes

```typescript
// app/api/presentations/route.ts
export async function GET(request: Request) {
  const supabase = createClient()
  const { data, error } = await supabase
    .from('presentations')
    .select('*')
    .order('updated_at', { ascending: false })

  return Response.json(data)
}

export async function POST(request: Request) {
  const { title, source_guide } = await request.json()

  // Call Supabase Edge Function to parse guide
  const { data } = await supabase.functions.invoke('parse-guide', {
    body: { guide: source_guide }
  })

  // Save to database
  const { data: presentation } = await supabase
    .from('presentations')
    .insert({ title, source_guide, slides_json: data.slides })
    .select()
    .single()

  return Response.json(presentation)
}
```

#### Supabase Edge Functions (Deno)

```typescript
// supabase/functions/parse-guide/index.ts
import { serve } from 'std/http/server.ts'
import Anthropic from '@anthropic-ai/sdk'

serve(async (req) => {
  const { guide } = await req.json()

  const anthropic = new Anthropic({
    apiKey: Deno.env.get('ANTHROPIC_API_KEY')!
  })

  const message = await anthropic.messages.create({
    model: 'claude-3-7-sonnet-20250219',
    max_tokens: 16000,
    messages: [{
      role: 'user',
      content: `Parse this facilitator guide: ${guide}`
    }]
  })

  return new Response(
    JSON.stringify({ slides: message.content }),
    { headers: { 'Content-Type': 'application/json' } }
  )
})
```

### Frontend Components

#### Editor Component (TipTap)

```typescript
// components/editor/SlideEditor.tsx
'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { useSlideStore } from '@/lib/stores/slides'

export function SlideEditor({ slideId }: { slideId: string }) {
  const { updateSlide, getSlide } = useSlideStore()
  const slide = getSlide(slideId)

  const editor = useEditor({
    extensions: [StarterKit],
    content: slide.content,
    onUpdate: ({ editor }) => {
      updateSlide(slideId, { content: editor.getHTML() })
    }
  })

  return (
    <div className="prose max-w-none">
      <EditorContent editor={editor} />
    </div>
  )
}
```

#### Preview Component

```typescript
// components/preview/SlidePreview.tsx
'use client'

import { useSlideStore } from '@/lib/stores/slides'

export function SlidePreview({ slideId }: { slideId: string }) {
  const slide = useSlideStore(state => state.slides[slideId])

  const layouts = {
    title: <TitleLayout {...slide} />,
    content: <ContentLayout {...slide} />,
    two_columns: <TwoColumnLayout {...slide} />,
    // ... other layouts
  }

  return (
    <div className="aspect-video bg-white rounded-lg shadow-lg p-8">
      {layouts[slide.layout] || <ContentLayout {...slide} />}
    </div>
  )
}
```

### Real-time Collaboration

```typescript
// lib/realtime.ts
import { createClient } from '@/lib/supabase/client'

export function setupRealtimeCollaboration(presentationId: string) {
  const supabase = createClient()

  // Listen to slide updates
  const channel = supabase
    .channel(`presentation:${presentationId}`)
    .on('postgres_changes',
      { event: 'UPDATE', schema: 'public', table: 'slides' },
      (payload) => {
        // Update local state
        useSlideStore.getState().updateSlide(payload.new.id, payload.new)
      }
    )
    .on('presence', { event: 'sync' }, () => {
      const state = channel.presenceState()
      // Update cursor positions
    })
    .subscribe()

  return () => channel.unsubscribe()
}
```

### Deployment

#### Frontend (Vercel)

```bash
# Install Vercel CLI
npm i -g vercel

# Link project
vercel link

# Deploy
vercel --prod
```

**Automatic Features**:
- ✅ GitHub integration (auto-deploy on push)
- ✅ Preview deployments for PRs
- ✅ Edge network (global CDN)
- ✅ Automatic HTTPS
- ✅ Environment variables

#### Backend (Supabase)

```bash
# Install Supabase CLI
npm i -g supabase

# Link project
supabase link --project-ref your-project-ref

# Push database migrations
supabase db push

# Deploy Edge Functions
supabase functions deploy parse-guide
supabase functions deploy export-pptx
```

### Cost Estimation

| Service | Free Tier | Paid Tier (if needed) |
|---------|-----------|----------------------|
| **Vercel** | 100GB bandwidth/month<br/>100 builds/month | $20/month - Pro |
| **Supabase** | 500MB database<br/>1GB storage<br/>2GB egress | $25/month - Pro |
| **Imgur API** | Unlimited anonymous uploads | Free |
| **Anthropic API** | Pay-as-you-go | ~$0.50-2/presentation |

**Total**: Free for development, ~$45/month for production + API costs

---

## Development Roadmap

### Phase 1 & 2: ✅ COMPLETE
- [x] Imgur API integration
- [x] PPTX exporter (python-pptx)
- [x] reveal.js exporter
- [x] Unified export CLI

### Phase 3: API & Database (2-3 weeks)
- [ ] Set up Supabase project
- [ ] Create database schema
- [ ] Implement RLS policies
- [ ] Create Edge Functions for processing
- [ ] Set up Supabase Storage

### Phase 4: Web UI MVP (3-4 weeks)
- [ ] Next.js 14 project setup
- [ ] Authentication (Supabase Auth)
- [ ] Dashboard (list presentations)
- [ ] Editor (TipTap integration)
- [ ] Preview (side-by-side)
- [ ] Export (download PPTX/HTML)

### Phase 5: Collaboration (3-4 weeks)
- [ ] Real-time presence
- [ ] Cursor tracking
- [ ] Comments system
- [ ] Version history
- [ ] Sharing & permissions

### Phase 6: Advanced Features (ongoing)
- [ ] Template marketplace
- [ ] AI suggestions
- [ ] Image search integration
- [ ] Multi-language support
- [ ] Analytics dashboard
- [ ] Mobile app (React Native)

---

## Getting Started (Phase 3+)

### 1. Set up Supabase

```bash
# Create new Supabase project at supabase.com
# Copy .env.example to .env.local
cp .env.example .env.local

# Add Supabase credentials
NEXT_PUBLIC_SUPABASE_URL=your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key
```

### 2. Set up Next.js

```bash
# Create Next.js app
npx create-next-app@latest makeslides-web --typescript --tailwind --app

# Install dependencies
cd makeslides-web
npm install @supabase/supabase-js @supabase/auth-helpers-nextjs
npm install @tiptap/react @tiptap/starter-kit
npm install @dnd-kit/core @dnd-kit/sortable
npm install zustand react-hook-form zod
```

### 3. Run Development

```bash
# Start Next.js dev server
npm run dev

# Start Supabase locally (optional)
supabase start
```

---

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)
- [TipTap Documentation](https://tiptap.dev)
- [Vercel Documentation](https://vercel.com/docs)
