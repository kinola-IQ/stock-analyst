# Vercel Speed Insights Setup

This document explains how Vercel Speed Insights has been configured for the Stock Analyst API project.

## What is Vercel Speed Insights?

Vercel Speed Insights is a frontend performance monitoring tool that tracks Web Vitals (Core Web Vitals) in real-time, including:
- **LCP (Largest Contentful Paint)**: Loading performance
- **FID (First Input Delay)**: Interactivity
- **CLS (Cumulative Layout Shift)**: Visual stability
- **FCP (First Contentful Paint)**: First render timing
- **TTFB (Time to First Byte)**: Server response time

## Implementation

### What Has Been Configured

Since this is a FastAPI backend API, Speed Insights has been integrated into a landing page:

1. **Static HTML Page** (`static/index.html`)
   - Added a landing page with Vercel Speed Insights script
   - Includes the Speed Insights initialization code
   - Provides links to API documentation and health checks

2. **FastAPI Configuration** (`main.py`)
   - Mounted the `/static` directory to serve static files
   - Added a root route (`/`) that serves the landing page
   - Landing page includes the Speed Insights tracking script

### Speed Insights Implementation

The following code has been added to `static/index.html`:

```html
<!-- Vercel Speed Insights -->
<script>
    window.si = window.si || function () { (window.siq = window.siq || []).push(arguments); };
</script>
<script defer src="/_vercel/speed-insights/script.js"></script>
```

This is the vanilla JavaScript implementation as documented in the [official Vercel Speed Insights Quickstart Guide](https://vercel.com/docs/speed-insights/quickstart).

## Enabling Speed Insights on Vercel

To activate Speed Insights tracking, follow these steps:

### 1. Enable Speed Insights in Vercel Dashboard

1. Navigate to your project in the [Vercel Dashboard](https://vercel.com/dashboard)
2. Go to **Settings** → **Speed Insights**
3. Click the **Enable** button
4. This will add new routes at `/_vercel/speed-insights/*` after your next deployment

### 2. Deploy Your Application

Deploy your application to Vercel:

```bash
vercel deploy
```

Or push to your connected Git repository for automatic deployment.

### 3. Verify Installation

After deployment:

1. Visit your application's homepage (root URL)
2. Open browser DevTools → Network tab
3. Look for a request to `/_vercel/speed-insights/script.js`
4. If present, Speed Insights is successfully configured

### 4. View Analytics

1. Return to your Vercel Dashboard
2. Navigate to **Analytics** → **Speed Insights**
3. View real-time Web Vitals data from your users

## Important Notes

### Backend APIs and Speed Insights

**Important:** Vercel Speed Insights is a **frontend performance monitoring tool** designed to track Web Vitals in browser environments. It:

- ✅ Works with web pages (HTML, JavaScript, React, Vue, Next.js, etc.)
- ❌ Cannot monitor pure API endpoints (JSON responses)
- ❌ Does not track backend performance metrics

Since this is primarily a FastAPI backend API:

- The landing page (`/`) will track Speed Insights metrics
- API endpoints (`/v1/*`, `/health`, etc.) will not generate Speed Insights data
- Speed Insights data will only be collected when users visit the root HTML page

### For API-Only Deployments

If you prefer to run this as a pure API without a landing page:

1. Remove the `static/` directory
2. Remove the Speed Insights script references
3. Use Vercel's [Functions Monitoring](https://vercel.com/docs/observability/runtime-logs) instead for backend performance

### Adding Speed Insights to a Frontend

If you build a frontend application (React, Vue, Next.js, etc.) that consumes this API:

1. Install `@vercel/speed-insights` in your frontend project:
   ```bash
   npm install @vercel/speed-insights
   # or
   pnpm add @vercel/speed-insights
   ```

2. Follow framework-specific integration:
   - **Next.js**: Import from `@vercel/speed-insights/next`
   - **React**: Import from `@vercel/speed-insights/react`
   - **Vue**: Import from `@vercel/speed-insights/vue`
   - **SvelteKit**: Use `injectSpeedInsights()` from `@vercel/speed-insights/sveltekit`

See the [official documentation](https://vercel.com/docs/speed-insights/quickstart) for detailed instructions.

## Development vs Production

**Note:** Speed Insights **does not track data in development mode**. You must deploy to Vercel to see metrics.

To test locally:
```bash
# The page will load, but no metrics will be sent
uvicorn main:app --host 0.0.0.0 --port 8080
```

To see actual Speed Insights data:
- Deploy to Vercel
- Visit the deployed URL
- Check the Vercel Dashboard for metrics

## Troubleshooting

### Script Not Loading

If the Speed Insights script doesn't load:

1. Verify you enabled Speed Insights in the Vercel Dashboard
2. Ensure you deployed after enabling
3. Check that you're on a Vercel deployment (not localhost)
4. Verify the script URL in your browser DevTools

### No Data in Dashboard

If enabled but no data appears:

1. Speed Insights only tracks in production (not development)
2. Requires actual user visits to generate data
3. May take a few minutes for data to appear
4. Check that JavaScript is enabled in your browser

## Resources

- [Vercel Speed Insights Documentation](https://vercel.com/docs/speed-insights)
- [Speed Insights Quickstart](https://vercel.com/docs/speed-insights/quickstart)
- [Web Vitals Overview](https://web.dev/vitals/)
- [Core Web Vitals](https://web.dev/vitals/#core-web-vitals)

## Summary

Vercel Speed Insights has been integrated into this FastAPI application via a landing page. The implementation follows the official Vercel documentation for vanilla JavaScript/static HTML sites. To activate tracking, enable Speed Insights in your Vercel Dashboard and deploy your application.
