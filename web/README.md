# Workday Web Frontend

Next.js-based web interface for Workday timeline tracker.

## Features

- 📅 **Timeline View**: Browse your daily activities
- 🎯 **Activity Details**: View detailed information about each activity
- 🎨 **Clean UI**: Inspired by Dayflow's design
- ⚡ **Static Export**: Served by FastAPI backend

## Development

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Python backend running (see main README)

### Installation

```bash
# Install dependencies
npm install
# or
yarn install
# or
pnpm install
```

### Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

## Build for Production

```bash
# Build and export static files
npm run build
```

This will create an `out/` directory with static files that can be served by FastAPI.

## Project Structure

```
web/
├── src/
│   ├── app/              # Next.js app router pages
│   │   ├── layout.tsx    # Root layout with sidebar
│   │   ├── page.tsx      # Home page (Timeline)
│   │   ├── dashboard/    # Dashboard page
│   │   └── settings/     # Settings page
│   ├── components/       # React components
│   │   ├── Sidebar.tsx
│   │   ├── Header.tsx
│   │   ├── TimelineList.tsx
│   │   └── ActivityDetail.tsx
│   ├── lib/             # Utilities
│   │   ├── api.ts       # API client
│   │   └── utils.ts     # Helper functions
│   └── types/           # TypeScript types
│       └── index.ts
├── public/              # Static assets
├── package.json
├── next.config.js       # Next.js configuration
├── tailwind.config.js   # Tailwind CSS configuration
└── tsconfig.json        # TypeScript configuration
```

## API Integration

The frontend communicates with the FastAPI backend through the API client (`src/lib/api.ts`).

Default API base URL: `http://localhost:8000`

You can override this by setting the `NEXT_PUBLIC_API_URL` environment variable.

## Styling

- **Tailwind CSS**: Utility-first CSS framework
- **Custom Colors**: Defined in `tailwind.config.js`
- **Responsive Design**: Mobile-friendly layout

## Design Inspiration

The UI is inspired by [Dayflow](https://github.com/dayflow-ai/dayflow):
- Clean, minimal interface
- Two-column layout (timeline + details)
- Serif fonts for headers
- Subtle shadows and rounded corners
