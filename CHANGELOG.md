# Changelog

## [0.2.0](https://github.com/nhinata/nibs/compare/v0.1.0...v0.2.0) (2026-11-04)


### Features

* record each page's headings and how it was read in the usage log ([#12](https://github.com/nhinata/nibs/issues/12)) ([397c90e](https://github.com/nhinata/nibs/commit/397c90e389d2feb646f2be19c66d2267338ce390))


### Bug Fixes

* find where sections end in one pass over the headings ([#14](https://github.com/nhinata/nibs/issues/14)) ([5d12dc1](https://github.com/nhinata/nibs/commit/5d12dc1337309d0327c1b8b1aa9140538dd430d8))
* refuse --max and --limit below 1 ([#18](https://github.com/nhinata/nibs/issues/18)) ([075d2d9](https://github.com/nhinata/nibs/commit/075d2d9bcdfa82b7cd798be377117c62cc6610ea))

## 0.1.0 (2026-11-03)


### Features

* read a web page by its headings ([6e42fc1](https://github.com/nhinata/nibs/commit/6e42fc1571dc3a17e93febf0caed0db9d289857d))


### Bug Fixes

* close a code fence only with one at least as long ([#10](https://github.com/nhinata/nibs/issues/10)) ([e4c363d](https://github.com/nhinata/nibs/commit/e4c363d66e23bc12209a5d2cf74925f532b180b4))
* keep article headers, forms and code blocks when reading HTML ([#4](https://github.com/nhinata/nibs/issues/4)) ([7ff6281](https://github.com/nhinata/nibs/commit/7ff62811e90ba1530804212c997fb0eea10782ad))
* read only http and https URLs ([#2](https://github.com/nhinata/nibs/issues/2)) ([11dd070](https://github.com/nhinata/nibs/commit/11dd070561fb2a1fb682ecadaeab9d1224b24aed))
* read the charset a page declares in a meta tag ([#5](https://github.com/nhinata/nibs/issues/5)) ([478c52e](https://github.com/nhinata/nibs/commit/478c52ead8fb284a0b1d8cdfb5c4bf145122b28c))
* show a message instead of a traceback on broken input ([#6](https://github.com/nhinata/nibs/issues/6)) ([6d603c2](https://github.com/nhinata/nibs/commit/6d603c29036f55f68e8328f5e82c5cb74ea12495))
