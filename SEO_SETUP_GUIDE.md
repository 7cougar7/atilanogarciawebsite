# SEO Setup and Monitoring Guide

## Google Search Console Setup

### Step 1: Add Property to Google Search Console
1. Go to [Google Search Console](https://search.google.com/search-console/)
2. Click "Add Property"
3. Choose "URL prefix" and enter your domain: `https://atilanogarcia.com`
4. Verify ownership using one of these methods:
   - **HTML file upload** (recommended for Django)
   - **HTML tag** (add to base template)
   - **DNS record**
   - **Google Analytics**

### Step 2: HTML Tag Verification (Easiest for Django)
Add this meta tag to your base template `<head>` section:
```html
<meta name="google-site-verification" content="YOUR_VERIFICATION_CODE" />
```

### Step 3: Submit Sitemap
1. In Google Search Console, go to "Sitemaps"
2. Submit your sitemap URL: `https://atilanogarcia.com/sitemap.xml`
3. Monitor indexing status

### Step 4: Monitor Performance
- **Coverage**: Check for indexing issues
- **Performance**: Monitor clicks, impressions, CTR, position
- **Enhancements**: Check for mobile usability, Core Web Vitals
- **Security Issues**: Monitor for security problems

## Google Analytics 4 Setup

### Step 1: Create GA4 Property
1. Go to [Google Analytics](https://analytics.google.com/)
2. Create new GA4 property for your domain
3. Get your Measurement ID (format: G-XXXXXXXXXX)

### Step 2: Add GA4 to Django
Add this to your base template before closing `</head>`:
```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Step 3: Set Up Goals and Conversions
- **Contact form submissions**
- **Resume downloads**
- **Project page visits**
- **Time on site goals**

## Keyword Ranking Monitoring

### Recommended Tools:
1. **Google Search Console** (free) - Primary keyword tracking
2. **Ahrefs** (paid) - Comprehensive SEO analysis
3. **SEMrush** (paid) - Keyword research and tracking
4. **Ubersuggest** (freemium) - Basic keyword tracking

### Target Keywords to Monitor:
- "Atilano Garcia"
- "Atilano Garcia software engineer"
- "Tilo Garcia developer"
- "Software engineer portfolio"
- "Django developer"
- "Machine learning engineer"
- "Web developer Texas"
- "UT software engineer"

## SEO Performance Metrics to Track

### Primary Metrics:
- **Organic Traffic Growth**: Target 25% increase in 3 months
- **Keyword Rankings**: Track top 10 target keywords
- **Click-Through Rate (CTR)**: Target 3-5% average CTR
- **Bounce Rate**: Target <60% for key pages
- **Page Load Speed**: Target <3 seconds
- **Core Web Vitals**: All metrics in "Good" range

### Secondary Metrics:
- **Backlink Growth**: Monitor referring domains
- **Social Shares**: Track social media engagement
- **Brand Searches**: Monitor "Atilano Garcia" searches
- **Local SEO**: If applicable for location-based searches

## Monthly SEO Checklist

### Week 1: Performance Review
- [ ] Review Google Search Console performance
- [ ] Check Google Analytics traffic data
- [ ] Monitor keyword ranking changes
- [ ] Review Core Web Vitals scores

### Week 2: Content Optimization
- [ ] Update meta descriptions if CTR is low
- [ ] Add new internal links to recent content
- [ ] Optimize underperforming pages
- [ ] Check for broken links

### Week 3: Technical SEO
- [ ] Review site speed performance
- [ ] Check mobile usability issues
- [ ] Verify sitemap is up to date
- [ ] Monitor crawl errors

### Week 4: Competitive Analysis
- [ ] Research competitor keywords
- [ ] Analyze competitor content gaps
- [ ] Update keyword strategy
- [ ] Plan next month's SEO improvements

## SEO Alerts to Set Up

### Google Search Console Alerts:
- Coverage issues (indexing problems)
- Manual actions (penalties)
- Security issues
- Significant traffic drops

### Google Analytics Alerts:
- 20% traffic decrease week-over-week
- Unusual bounce rate increases
- Goal conversion drops
- Page load speed issues

## Success Benchmarks (3-Month Goals)

### Traffic Goals:
- **25% increase** in organic traffic
- **Top 10 rankings** for 5 target keywords
- **3%+ average CTR** from search results
- **50%+ increase** in brand searches

### Technical Goals:
- **90+ PageSpeed Insights** score
- **All Core Web Vitals** in "Good" range
- **Zero critical SEO issues** in Search Console
- **100% mobile-friendly** pages

### Engagement Goals:
- **<60% bounce rate** on key pages
- **2+ minutes** average session duration
- **2+ pages** per session
- **10%+ increase** in return visitors
