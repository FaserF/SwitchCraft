import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
    title: "SwitchCraft",
    description: "The Ultimate Packaging Assistant for IT Professionals - Streamline your application packaging workflow with smart analysis, Intune integration, and AI assistance.",

    base: process.env.BASE_URL || '/SwitchCraft/',

    // English only
    lang: 'en-US',

    head: [
        ['link', { rel: 'icon', href: '/favicon.ico' }],
        ['meta', { name: 'theme-color', content: '#6366f1' }],
        ['meta', { name: 'og:type', content: 'website' }],
        ['meta', { name: 'og:title', content: 'SwitchCraft - The Ultimate Packaging Assistant' }],
        ['meta', { name: 'og:description', content: 'Streamline your IT packaging workflow with smart analysis, Intune integration, and AI assistance.' }],
        ['meta', { name: 'og:image', content: 'https://github.com/FaserF/SwitchCraft/raw/main/docs/public/screenshots/switchcraft_logo_with_Text.png' }],
        ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ],

    // Clean URLs without .html
    cleanUrls: true,

    // Last updated timestamp
    lastUpdated: true,

    themeConfig: {
        logo: '/screenshots/switchcraft_logo_with_Text.png',
        siteTitle: 'SwitchCraft',

        nav: [
            { text: 'Home', link: '/' },
            { text: 'Guide', link: '/installation' },
            { text: 'Features', link: '/FEATURES' },
            {
                text: 'Enterprise',
                items: [
                    { text: 'Intune Integration', link: '/INTUNE' },
                    { text: 'Intune Setup Guide', link: '/INTUNE_SETUP' },
                    { text: 'OMA-URI Reference', link: '/IntuneConfig' },
                    { text: 'GPO / ADMX Policies', link: '/PolicyDefinitions/README' },
                    { text: 'Registry Settings', link: '/Registry' },
                    { text: 'Security Guide', link: '/SECURITY' }
                ]
            },
            { text: 'FAQ', link: '/faq' },
            {
                text: 'Download',
                link: 'https://github.com/FaserF/SwitchCraft/releases/latest'
            }
        ],

        sidebar: {
            '/': [
                {
                    text: 'Getting Started',
                    collapsed: false,
                    items: [
                        { text: 'Installation', link: '/installation' },
                        { text: 'Features Overview', link: '/FEATURES' },
                        { text: 'Winget Store', link: '/WINGET' },
                        { text: 'Upgrading', link: '/upgrade' }
                    ]
                },
                {
                    text: 'Core Functionality',
                    collapsed: false,
                    items: [
                        { text: 'CLI Reference', link: '/CLI_Reference' },
                        { text: 'Addon System', link: '/ADDONS' },
                        { text: 'Cloud Sync', link: '/CLOUDSYNC' },
                        { text: 'Cloud Sync Setup', link: '/setup_cloudsync' }
                    ]
                },
                {
                    text: 'Enterprise & IT Pro',
                    collapsed: false,
                    items: [
                        { text: 'Intune Integration', link: '/INTUNE' },
                        { text: 'Intune Setup Guide', link: '/INTUNE_SETUP' },
                        { text: 'OMA-URI Reference', link: '/IntuneConfig' },
                        { text: 'GPO / ADMX Policies', link: '/PolicyDefinitions/README' },
                        { text: 'Registry Settings', link: '/Registry' },
                        { text: 'Security Guide', link: '/SECURITY' }
                    ]
                },
                {
                    text: 'Development',
                    collapsed: true,
                    items: [
                        { text: 'Building from Source', link: '/building' },
                        { text: 'CI Architecture', link: '/CI_Architecture' },
                        { text: 'Debugging API', link: '/Debugging_API' }
                    ]
                },
                {
                    text: 'Help',
                    collapsed: true,
                    items: [
                        { text: 'FAQ', link: '/faq' }
                    ]
                }
            ]
        },

        socialLinks: [
            { icon: 'github', link: 'https://github.com/FaserF/SwitchCraft' }
        ],

        footer: {
            message: 'Released under the MIT License',
            copyright: 'Copyright © 2025 FaserF'
        },

        search: {
            provider: 'local',
            options: {
                detailedView: true
            }
        },

        editLink: {
            pattern: 'https://github.com/FaserF/SwitchCraft/edit/main/docs/:path',
            text: 'Edit this page on GitHub'
        },

        lastUpdated: {
            text: 'Last updated',
            formatOptions: {
                dateStyle: 'medium'
            }
        },

        outline: {
            level: [2, 3],
            label: 'On this page'
        },

        docFooter: {
            prev: 'Previous',
            next: 'Next'
        },

        // Carbon ads or similar can be added here
        // carbonAds: { ... }
    },

    vite: {
        publicDir: 'public',
        build: {
            rollupOptions: {
                external: (id) => {
                    // Treat images in public directory as external static assets
                    // This prevents Vite from trying to import them as modules
                    if (typeof id === 'string' && (id.startsWith('/screenshots/') || id.includes('/screenshots/'))) {
                        return true
                    }
                    return false
                }
            }
        }
    }
})
