import { defineConfig } from 'vitepress'

// https://vitepress.dev/reference/site-config
export default defineConfig({
    title: "SwitchCraft",
    description: "Comprehensive packaging assistant for IT Professionals",
    themeConfig: {
        // https://vitepress.dev/reference/default-theme-config
        nav: [
            { text: 'Home', link: '/' },
            { text: 'Features', link: '/FEATURES' },
            { text: 'CLI', link: '/CLI_Reference' },
            { text: 'Enterprise', link: '/INTUNE' }
        ],

        sidebar: [
            {
                text: 'Getting Started',
                items: [
                    { text: 'Introduction', link: '/FEATURES' },
                    { text: 'Installation', link: '/WINGET' }
                ]
            },
            {
                text: 'Core Features',
                items: [
                    { text: 'Features & Analysis', link: '/FEATURES' },
                    { text: 'Winget Store', link: '/WINGET' },
                    { text: 'CLI Reference', link: '/CLI_Reference' }
                ]
            },
            {
                text: 'Enterprise & IT Pro',
                items: [
                    { text: 'Intune Integration', link: '/INTUNE' },
                    { text: 'Configuration (Registry)', link: '/Registry' },
                    { text: 'GPO / Policies', link: '/PolicyDefinitions/README' },
                    { text: 'Security Guide', link: '/SECURITY' }
                ]
            },
            {
                text: 'Advanced',
                items: [
                    { text: 'Addon System', link: '/ADDONS' },
                    { text: 'Cloud Sync', link: '/CLOUDSYNC' },
                    { text: 'CI Architecture', link: '/CI_Architecture' }
                ]
            }
        ],

        socialLinks: [
            { icon: 'github', link: 'https://github.com/FaserF/SwitchCraft' }
        ],

        footer: {
            message: 'Released under the MIT License.',
            copyright: 'Copyright © 2025-present FaserF'
        }
    }
})
