# Hentai2Read Metadata

Plugin for [happypandax](https://github.com/happypandax/happypandax) that fetches metadata from [Hentai2Read](https://hentai2read.com) and applies it for the gallery.

This plugin will only be useful if you have archives from Hentai2Read and haven't renamed them.
The search is based on the archive name minus the `chapter` suffix.

## Install

Download the plugin.
https://github.com/CarrotPancake/h2r-metadata/releases

Extract the archive.
You should have a directory named `h2r-metadata`.

Place the directory in happypandax' `plugins` directory.
It can probably be found in the happypandax root directory `{happypandaxroot}/plugins`.

The plugin then has to be installed from happypandax plugin view.
Currently found at `About -> Plugins`.
Simply scroll down until you find the plugin named `Hentai2Read Metadata` and click install.

See the install plugin section in the happypandax documentation for further details: [https://happypandax.github.io/usage.html#installing-plugins](https://happypandax.github.io/usage.html#installing-plugins)

## Usage

The plugin will automatically be used when querying for metadata.
No further action should be required by the user once installed.

## Changelog

- v0.2.1

  - Support decimal chapter names

- v0.2.0

  - Removes 'dj' suffix from parody
  - Sets archive category based on parody

- v0.1.0

  - Parses and sets additional metadata
  - Updates the chapter number based on the file name
  - Fixes too aggressive punctuation removal from data values
  - More selective tag parsing

- v0.0.1
  - Initial version
