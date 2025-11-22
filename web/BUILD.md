# Building the Static Frontend

This guide explains how to build the Next.js frontend as a static site.

## Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- All dependencies installed

## Build Steps

### 1. Install Dependencies

```bash
cd web
npm install
```

### 2. (Optional) Configure API URL

If your API is not running on `http://localhost:8000`, edit `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://your-api-server:8000
```

For production deployment, you can leave it empty to use relative URLs:

```bash
NEXT_PUBLIC_API_URL=
```

### 3. Build the Static Site

```bash
npm run build
```

This will:
- Compile TypeScript
- Bundle JavaScript and CSS
- Generate static HTML pages
- Output everything to the `out/` directory

### 4. Verify the Build

Check that the `out/` directory contains:
- `index.html` - Main page
- `_next/` - Next.js assets
- `dashboard/` - Dashboard page
- `settings/` - Settings page

### 5. Serve with FastAPI

The FastAPI backend automatically serves the static files from `web/out/`:

```bash
cd ..
python api.py
```

Then visit: `http://localhost:8000`

## Build Output

The static export creates a complete standalone website:

```
web/out/
├── index.html              # Homepage (Timeline)
├── dashboard/
│   └── index.html         # Dashboard page
├── settings/
│   └── index.html         # Settings page
├── _next/
│   ├── static/            # Static assets
│   │   ├── css/          # Compiled CSS
│   │   ├── chunks/       # JavaScript bundles
│   │   └── media/        # Fonts, images
│   └── ...
└── ...
```

## Troubleshooting

### Build fails with module not found

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
```

### API calls fail from static site

If the static site can't reach the API, check:

1. **CORS settings** - FastAPI has CORS enabled for all origins
2. **API URL** - Check `.env.local` or use relative URLs
3. **Network** - Ensure API server is running

### Static export warnings

Some Next.js features don't work with static export:
- ❌ Server-side rendering (getServerSideProps)
- ❌ API routes in Next.js
- ❌ Incremental Static Regeneration
- ✅ Client-side data fetching (our approach)
- ✅ Dynamic routes with generateStaticParams

## Development vs Production

### Development
```bash
npm run dev
```
- Hot reload
- Separate dev server (port 3000)
- Connects to API at `http://localhost:8000`

### Production
```bash
npm run build
```
- Static HTML files
- Served by FastAPI
- No separate frontend server needed

## Size Optimization

The built site should be around:
- **~500KB** - JavaScript bundles
- **~50KB** - CSS
- **~100KB** - Fonts

Total: Less than 1MB for fast loading.

## Caching

For production deployment, consider:
- Setting cache headers in FastAPI
- Using a CDN for `_next/static/` files
- Enabling gzip compression
