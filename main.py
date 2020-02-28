import __hpx__ as hpx

import re
import os
import urllib
import string

from bs4 import BeautifulSoup

log = hpx.get_logger(__name__)

CHAPTER_PATTERN = re.compile(r"_chapter_\d+\.?\w*$")

H2R_BASE_URL = "https://hentai2read.com"

@hpx.subscribe("init")
def inited():
    # Called when this plugin is initialised
    pass

@hpx.subscribe("disable")
def disabled():
    # Called when this plugin has been disiabled
    pass

@hpx.subscribe("remove")
def removed():
    # Called when this plugin is about to be removed
    pass

@hpx.subscribe('config_update')
def config_update(cfg):
    # TODO Anything in the plugin that should check the config?
    pass

@hpx.attach("Metadata.info")
def metadata_info():
    return hpx.command.MetadataInfo(
        identifier = "h2r-metadata",
        name = "Hentai2Read Metadata",
        description = "Extracts and applies metadata from Hentai2Read",
        sites= ("https://hentai2read.com",),
        models = (
            hpx.command.GetDatabaseModel("Gallery"),
        )
    )

@hpx.attach("Metadata.query", trigger="h2r-metadata")
def query(itemtuple):
    log.info("Trying to fetch metadata from hentai2read")
    meta_data = []

    for item in itemtuple:
        sources = item.item.get_sources()
        if sources:
            filename = os.path.split(sources[0])[1]
            filename = os.path.splitext(filename)[0]
            h2r_name = _to_h2r_name(filename)
            quoted_filename = urllib.parse.quote(h2r_name)

            h2r_url = urllib.parse.urljoin(H2R_BASE_URL, quoted_filename)
            
            chapter_number = _extract_chapter_number(filename)

            meta_data.append(hpx.command.MetadataData(
                    metadataitem = item,
                    data={
                        'h2r_url': h2r_url,
                        "chapter_number": chapter_number,
                        }))
    
    return tuple(meta_data)

def _to_h2r_name(filename):
    filename = CHAPTER_PATTERN.sub("", filename)
    return filename.lower()

def _extract_chapter_number(filename):
    match = CHAPTER_PATTERN.search(filename)
    if not match:
        log.debug(f"Did not find any chapter suffix in '{filename}'")
        return None
    
    chapter_suffix = match.group(0)
    number_match = re.search(r"\d", chapter_suffix)
    if not number_match:
        log.debug(f"Found no digits in '{chapter_suffix}'")
        return None
    
    chapter_number = int(number_match.group(0))
    log.debug(f"Extracted chapter number '{chapter_number}' from '{filename}'")
    return chapter_number

@hpx.attach("Metadata.apply", trigger="h2r-metadata")
def apply(datatuple):
    log.info("Applying metadata from hentai2read")
    results = []

    for item in datatuple:
        h2r_url = item.data["h2r_url"]
        r = hpx.command.SingleGETRequest().request(h2r_url)
        # TODO Might want to add logging for not ok response
        if r.ok:
            parsed_data = _parse_page(r.text, h2r_url, item.data.get("chapter_number"))
            log.debug(f"Parsed data from response: {parsed_data}")
            gallery_data = _map_to_hpx_gallery_data(item.item, parsed_data)
            log.debug(f"About to update item with gallery data: {gallery_data}")

            success = hpx.command.UpdateItemData(item.item, gallery_data)
            log.info(f"Updated item data: {success}")

            results.append(hpx.command.MetadataResult(data=item, status=success))
    return tuple(results)

def _parse_page(html, url, chapter_number):
    meta_data = {
      "artists": set(),
      "tags": [],
      "parodies": [],
      "url": url,
      "characters": [],
      "chapter_number": chapter_number,
      "category": "Manga"
    }

    soup = BeautifulSoup(html, "html.parser")

    url_pattern = re.compile(re.escape(url))
    title_elem = soup.find("a", {"href": url_pattern})
    if title_elem:
      title = title_elem.get_text()
      title = title.strip()
      if title:
        meta_data["title"] = title

    tag_buttons = soup.find_all(class_="tagButton")
    for tb in tag_buttons:
        text = tb.get_text()
        text = text.strip(string.whitespace + "-")
        if not text:
            continue
        
        bullet_name = _get_list_bullet_name(tb)
        if bullet_name == "artist" or bullet_name == "author":
            meta_data["artists"].add(text)
        elif (bullet_name == "parody"):
            parody = _parse_parody(text)
            meta_data["parodies"].append(parody)
            if parody:
                meta_data["category"] = "Doujinshi"
        elif (bullet_name == "language"):
            meta_data["language"] = text
        elif (bullet_name == "status"):
            meta_data["status"] = text
        elif (bullet_name == "character"):
            meta_data["characters"].append(text)
        elif (bullet_name == "category" or bullet_name == "content"):
            meta_data["tags"].append(text)

    story_bullet_name = soup.find("b", text="Storyline")
    if story_bullet_name:
      story_element = story_bullet_name.find_next_sibling("p")
      if story_element:
        text = story_element.get_text()
        if _has_description_text(text):
          meta_data["description"] = text

    return meta_data

def _get_list_bullet_name(tag_button):
    list_bullet = tag_button.find_previous_sibling("b")
    if not list_bullet:
        return None
    
    bullet_text = list_bullet.get_text()
    if not bullet_text:
        return None
  
    return bullet_text.lower().strip(string.whitespace + string.punctuation)

def _has_description_text(text):
    if not text:
        return False
    no_description_pattern = re.compile(r"[Nn]othing yet")
    return not no_description_pattern.match(text)

def _parse_parody(parody_text):
    doujnshi_pattern = re.compile(r"dj\.?\s*$", re.IGNORECASE)
    return re.sub(doujnshi_pattern, "", parody_text).strip()

def _map_to_hpx_gallery_data(gallery, meta_data):
    """
    hpx_model = {
        'titles': None, # [(title, language),...]
        'artists': None, # [(artist, (circle, circle, ..)),...]
        'parodies': None, # [parody, ...]
        'category': None,
        'tags': None, # [tag, tag, tag, ..] or {ns:[tag, tag, tag, ...]}
        'pub_date': None, # DateTime object or Arrow object
        'language': None,
        'urls': None # [url, ...]
    }
    """
    gallery_data = hpx.command.GalleryData()
    
    if len(meta_data["artists"]) > 0:
        artists = []
        for artist in meta_data["artists"]:
            artist_data = hpx.command.ArtistData(names=[hpx.command.ArtistNameData(name=string.capwords(artist))])
            artists.append(artist_data)
        gallery_data.artists = artists
    
    title = meta_data.get("title")
    if title:
        title_data = hpx.command.TitleData(name=title)
        title_data.language = hpx.command.LanguageData(name="english")
        gallery_data.titles = [title_data]

        status = None
        if meta_data.get("status"):
            status = hpx.command.StatusData(name=meta_data["status"])
        gallery_data.grouping = hpx.command.GroupingData(name=title, status=status)

    tags = _map_to_hpx_gallery_tags(meta_data)
    if len(tags) > 0:
        gallery_data.tags = tags
    
    if len(meta_data["parodies"]) > 0:
        parodies = []
        for parody in meta_data["parodies"]:
            parodies.append(hpx.command.ParodyData(names=[hpx.command.ParodyNameData(name=string.capwords((parody)))]))

        if parodies:
            gallery_data.parodies = parodies
    
    if meta_data.get("url"):
        gallery_data.urls = [hpx.command.UrlData(name=meta_data["url"])]
    if meta_data.get("language"):
        gallery_data.language = hpx.command.LanguageData(name=meta_data["language"])
    if meta_data.get("description"):
        gallery_data.info = meta_data.get("description")
    if meta_data.get("chapter_number"):
        gallery_data.number = meta_data["chapter_number"]

    if "category" in meta_data:
        gallery_data.category = hpx.command.CategoryData(name=string.capwords(meta_data["category"]))
    
    return gallery_data

def _map_to_hpx_gallery_tags(meta_data):
    tags = []

    if len(meta_data["tags"]) > 0:
        for tag in meta_data["tags"]:
            tag_data = hpx.command.TagData(name=tag)
            tags.append(hpx.command.NamespaceTagData(tag=tag_data))

    if len(meta_data["characters"]) > 0:
        for tag in meta_data["characters"]:
            tag_data = hpx.command.TagData(name=tag)
            namespace_data = hpx.command.NamespaceData(name="character")
            tags.append(hpx.command.NamespaceTagData(tag=tag_data, namespace=namespace_data))
    
    return tags