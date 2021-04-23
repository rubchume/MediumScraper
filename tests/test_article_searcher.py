import unittest

import requests_mock

from src.article_searcher import ArticleSearcher


class ArticleSearcherTests(unittest.TestCase):
    def test_get_urls_from_search_results(self):
        # Given
        with open("tests/helpers/example_search_result_1.html", "r", encoding="utf-8") as file:
            search_result = file.read()

        # When
        urls = ArticleSearcher.get_article_urls(search_result)
        # Then
        self.assertEqual(
            [
                'https://medium.com/airbnb-engineering/experimentation-measurement-for-search-engine-optimization-b64136629760',
                'https://medium.com/blogging-guide/medium-article-search-engine-optimization-medium-seo-9249f18e8e76',
                'https://medium.com/cool-code-pal/'
                'introducing-web-components-and-what-it-means-for-search-engine-optimization-and-privacy-b21bfc1f63c7',
                'https://medium.com/the-logician/seo-guide-d534b69ce1c7',
                'https://medium.com/@myxys/seo-101-complete-search-engine-optimization-guide-checklist-97153741cfe6',
                'https://medium.com/write-to-blog/'
                'how-to-learn-search-engine-optimization-for-beginning-bloggers-765fe895d2d3',
                'https://medium.com/swlh/why-i-suck-at-search-engine-optimization-7777e6d0441f',
                'https://medium.com/age-of-awareness/'
                'search-engine-optimization-seo-for-new-writers-what-it-is-and-why-you-should-care-d36b8a1d000d',
                'https://medium.datadriveninvestor.com/'
                'why-seo-is-more-than-just-search-engine-optimization-285f75337702',
                'https://medium.com/@tyohan/'
                'progressive-web-app-search-engine-optimization-in-shuvayatra-app-a7c111671338'
            ],
            urls
        )

    @requests_mock.Mocker()
    def test_get_urls_from_search_term_for_just_10_results(self, mock):
        with open("tests/helpers/example_search_result_1.html", "r", encoding="utf-8") as file:
            mock.get("https://medium.com/search?q=mySearchTerm", text=file.read())
        article_searcher = ArticleSearcher()
        article_searcher.start(search_term="mySearchTerm")
        # When
        urls = article_searcher.get_next_article_urls(num_articles=10)
        # Then
        self.assertEqual(1, mock.call_count)
        self.assertEqual("https://medium.com/search?q=mySearchTerm", mock.request_history[0].url)
        self.assertEqual(
            [
                'https://medium.com/airbnb-engineering/experimentation-measurement-for-search-engine-optimization-b64136629760',
                'https://medium.com/blogging-guide/medium-article-search-engine-optimization-medium-seo-9249f18e8e76',
                'https://medium.com/cool-code-pal/'
                'introducing-web-components-and-what-it-means-for-search-engine-optimization-and-privacy-b21bfc1f63c7',
                'https://medium.com/the-logician/seo-guide-d534b69ce1c7',
                'https://medium.com/@myxys/seo-101-complete-search-engine-optimization-guide-checklist-97153741cfe6',
                'https://medium.com/write-to-blog/'
                'how-to-learn-search-engine-optimization-for-beginning-bloggers-765fe895d2d3',
                'https://medium.com/swlh/why-i-suck-at-search-engine-optimization-7777e6d0441f',
                'https://medium.com/age-of-awareness/'
                'search-engine-optimization-seo-for-new-writers-what-it-is-and-why-you-should-care-d36b8a1d000d',
                'https://medium.datadriveninvestor.com/'
                'why-seo-is-more-than-just-search-engine-optimization-285f75337702',
                'https://medium.com/@tyohan/'
                'progressive-web-app-search-engine-optimization-in-shuvayatra-app-a7c111671338'
            ],
            urls
        )

    @requests_mock.Mocker()
    def test_get_urls_from_search_term_for_multiple_results(self, mock):
        with open("tests/helpers/seo_search_result_1.html", "r", encoding="utf-8") as file:
            mock.get("https://medium.com/search?q=mySearchTerm", text=file.read())
        with open("tests/helpers/seo_search_result_2.html", "r", encoding="utf-8") as file:
            mock.get(
                "https://medium.com/search/posts?q=mySearchTerm"
                "&count=10"
                "&ignore=1b903b3ab6bb"
                "&ignore=92fad4f5a39"
                "&ignore=73ce840d8bb6"
                "&ignore=74ce5015c0c9"
                "&ignore=a6354595e400"
                "&ignore=b0c8230a8200"
                "&ignore=914e0fc3ab1"
                "&ignore=a3b3115a294b"
                "&ignore=ae4e5e7839e"
                "&ignore=3c46274501b2",
                text=file.read()
            )

        with open("tests/helpers/seo_search_result_3.html", "r", encoding="utf-8") as result3:
            with open("tests/helpers/seo_search_result_4.html", "r", encoding="utf-8") as result4:
                mock.post(
                    "https://medium.com/search/posts?q=mySearchTerm",
                    [{"text": result3.read(), "status_code": 200}, {"text": result4.read(), "status_code": 200}]
                )

        article_searcher = ArticleSearcher()
        article_searcher.start(search_term="mySearchTerm")
        # When
        urls = article_searcher.get_next_article_urls(num_articles=40)
        # Then
        self.assertEqual(4, mock.call_count)

        self.assertEqual("https://medium.com/search?q=mySearchTerm", mock.request_history[0].url)
        self.assertEqual(
            "https://medium.com/search/posts?q=mySearchTerm"
            "&count=10"
            "&ignore=1b903b3ab6bb"
            "&ignore=92fad4f5a39"
            "&ignore=73ce840d8bb6"
            "&ignore=74ce5015c0c9"
            "&ignore=a6354595e400"
            "&ignore=b0c8230a8200"
            "&ignore=914e0fc3ab1"
            "&ignore=a3b3115a294b"
            "&ignore=ae4e5e7839e"
            "&ignore=3c46274501b2",
            mock.request_history[1].url
        )
        self.assertEqual("https://medium.com/search/posts?q=mySearchTerm", mock.request_history[2].url)
        self.assertEqual(
            {
                "ignoredIds": [
                    "1b903b3ab6bb", "92fad4f5a39", "73ce840d8bb6", "74ce5015c0c9", "a6354595e400",
                    "b0c8230a8200", "914e0fc3ab1", "a3b3115a294b", "ae4e5e7839e", "3c46274501b2",
                    "1417625ce686", "5d1bf3af73db", "128f5f3a863c", "82c82d8e10db", "32399c49b2e5",
                    "edc4c0c8284b", "fddd5994e3e5", "9249f18e8e76", "5ed31d5edfe1", "bc06b8ca2383"
                ],
                "page": 3,
                "pageSize": 10
            },
            mock.request_history[2].json()
        )

        self.assertEqual("https://medium.com/search/posts?q=mySearchTerm", mock.request_history[3].url)
        self.assertEqual(
            {
                "ignoredIds": ["6328d19a1710", "7cd6d1e23de", "5a330c0e6eb2", "d1de6b170e2", "1f74e706ab11",
                               "1299f675c638", "70f0f17f46c6", "58ae831021b4", "23d523b031a1", "be2c827f1c38"],
                "page": 4,
                "pageSize": 10
            },
            mock.request_history[3].json()
        )

        self.assertEqual(
            [
                'https://medium.com/startup-grind/'
                'seo-is-not-hard-a-step-by-step-seo-tutorial-for-beginners-that-will-get-you-ranked-every-single-1b903b3ab6bb',
                'https://medium.com/free-code-camp/seo-secrets-reverse-engineering-googles-algorithm-92fad4f5a39',
                'https://medium.com/ol-portal-steps-forward-to-the-future-communicatio/'
                'blockchain-conference-of-olportal-and-hedera'
                '-hashgraph-projects-the-presentation-of-our-seo-73ce840d8bb6',
                'https://medium.com/free-code-camp/'
                'seo-vs-react-is-it-neccessary-to-render-react-pages-in-the-backend-74ce5015c0c9',
                'https://medium.com/@prestonwallace/'
                '3-ways-improve-react-seo-without-isomorphic-app-a6354595e400',
                'https://medium.com/creators-hub/'
                'seo-tips-to-make-your-stories-discoverable-and-grow-your-readership-b0c8230a8200',
                'https://medium.com/free-code-camp/'
                'using-fetch-as-google-for-seo-experiments-with-react-driven-websites-914e0fc3ab1',
                'https://entrepreneurshandbook.co/'
                'the-best-shortest-marketing-seo-checklist-ever-from-reddit-a3b3115a294b',
                'https://medium.com/@thejungwon/best-html-css-javascript-practice-chrome-extension-ae4e5e7839e',
                'https://chatbotsmagazine.com/19-best-practices-for-building-chatbots-3c46274501b2',
                'https://medium.com/as-a-product-designer/seo-sem-and-web-design-for-long-pages-1417625ce686',
                'https://medium.com/marketing-and-entrepreneurship/'
                '6-seo-experiments-that-will-blow-your-mind-5d1bf3af73db',
                'https://medium.com/@joseperezaguera/por-qu%C3%A9-no-hay-seo-en-mercadona-online-128f5f3a863c',
                'https://medium.com/%E4%B8%80%E4%BA%BA%E9%9B%9C%E8%AA%8C%E7%A4%BE/'
                '%E9%9B%B6%E5%BB%A3%E5%91%8A%E9%A0%90%E7%AE%97-%E6%88%91%E5%A6%82%E4%BD%95%E7%94%A8-seo-'
                '%E5%B0%8F%E6%8A%80%E5%B7%A7%E5%AF%AB%E5%87%BA-google-%E8%87%AA%E7%84%B6%E6%90%9C%E5%B0%8B%E7%AC%AC-1-'
                '%E4%BD%8D%E7%9A%84%E6%96%87%E7%AB%A0-82c82d8e10db',
                'https://medium.com/vue-mastery/best-practices-for-nuxt-js-seo-32399c49b2e5',
                'https://towardsdatascience.com/'
                'trend-seasonality-moving-average-auto-regressive-model'
                '-my-journey-to-time-series-data-with-edc4c0c8284b',
                'https://medium.com/y-pointer/2000-followers-fddd5994e3e5',
                'https://medium.com/blogging-guide/medium-article-search-engine-optimization-medium-seo-9249f18e8e76',
                'https://bettermarketing.pub/very-basic-seo-for-tech-neophytes-5ed31d5edfe1',
                'https://medium.com/@benjburkholder/'
                'javascript-seo-server-side-rendering-vs-client-side-rendering-bc06b8ca2383',
                'https://bettermarketing.pub/the-complete-guide-to-seo-in-2020-6328d19a1710',
                'https://medium.com/@barthbamasta/devenir-un-expert-en-seo-en-30min-7cd6d1e23de',
                'https://medium.com/@randfish/moz-returns-to-seo-5a330c0e6eb2',
                'https://medium.com/the-mission/overcome-the-google-gods-the-best-seo-learning-tools-d1de6b170e2',
                'https://medium.com/@lucamug/'
                'spa-and-seo-is-googlebot-able-to-render-a-single-page-application-1f74e706ab11',
                'https://medium.com/@cathyseo/the-product-designer-role-1299f675c638',
                'https://towardsdatascience.com/'
                'medical-image-segmentation-part-1-unet-convolutional-networks-with-interactive-code-70f0f17f46c6',
                'https://medium.com/@eytii/instagram-seo-%E7%B0%A1%E6%98%93%E4%B8%83%E6%92%87%E6%AD%A5-58ae831021b4',
                'https://medium.com/madhash/20-must-know-facts-about-seo-23d523b031a1',
                'https://medium.com/js-dojo/is-my-single-page-app-seo-friendly-be2c827f1c38',
                'https://medium.com/swlh/the-secret-to-my-long-tail-seo-success-13f18285f633',
                'https://medium.com/muddyum/'
                'in-search-of-the-meaning-of-seo-and-why-optimizing-matters-a-how-to-guide-7633dd568556',
                'https://bettermarketing.pub/how-to-improve-your-seo-for-free-write-damn-good-content-dc06cc119772',
                'https://towardsdatascience.com/'
                'understanding-2d-dilated-convolution-operation'
                '-with-examples-in-numpy-and-tensorflow-with-d376b3972b25',
                'https://towardsdatascience.com/'
                'paper-summary-matrix-factorization-techniques-for-recommender-systems-82d1a7ace74',
                'https://medium.com/pinterest-engineering/demystifying-seo-with-experiments-a183b325cf4c',
                'https://medium.com/erianmarketing/'
                '%E6%96%87%E6%A1%88%E8%A6%81%E6%80%8E%E9%BA%BC%E6%B7%B1%E5%85%A5%E4%BA%BA%E5%BF%83'
                '-5%E6%AD%A5%E9%A9%9F%E8%A1%8C%E9%8A%B7%E6%96%87%E6%A1%88%E6%92%B0%E5%AF%AB%E6%8A%80%E5%B7%A7'
                '-%E4%B8%8D%E9%9D%A0%E9%9D%88%E6%84%9F%E5%B0%B1%E8%AE%93%E9%A1%A7%E5%AE%A2%E5%90%B8%E7%9D%9B%E8%B2%B7%E5'
                '%96%AE-%E6%8F%90%E5%8D%87seo%E6%8E%92%E5%90%8D-b820dd6c4700',
                'https://medium.com/design-doordash/becoming-a-leader-as-a-first-generation-immigrant-4b9a883489dc',
                'https://medium.com/codingthesmartway-com-blog/'
                'angular-seo-making-angular-6-single-page-web-apps-search-engine-friendly-c8ec4ff2f549',
                'https://towardsdatascience.com/'
                'back-to-basics-deriving-back-propagation-on-simple-rnn-lstm-feat-aidan-gomez-c7f286ba973d'
            ],
            urls
        )
