import json
from os import getenv
from typing import Any, Dict, List, Optional, Union

from agno.tools import Toolkit
from agno.utils.log import log_error

try:
    from olostep import Olostep
except ImportError:
    raise ImportError("`olostep` not installed. Please install using `pip install olostep`")


class CustomJSONEncoder(json.JSONEncoder):
    """JSON encoder that falls back to ``str`` for non-serializable objects."""

    def default(self, o):
        try:
            return super().default(o)
        except TypeError:
            return str(o)


def _to_json(result: Any) -> str:
    """Serialize an Olostep SDK response (pydantic model, iterable, dict, ...) to JSON."""
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(), cls=CustomJSONEncoder)
    if hasattr(result, "to_dict"):
        return json.dumps(result.to_dict(), cls=CustomJSONEncoder)
    return json.dumps(result, cls=CustomJSONEncoder)


class OlostepTools(Toolkit):
    """
    Olostep is a web scraping, crawling, sitemap and AI answers API.

    Docs: https://docs.olostep.com
    Package: https://pypi.org/project/olostep/ (``pip install olostep``)

    Args:
        api_key (Optional[str]): Olostep API key. Falls back to ``OLOSTEP_API_KEY`` env var.
        enable_scrape (bool): Enable single-page scraping. Default True.
        enable_answers (bool): Enable AI answers endpoint. Default True.
        enable_crawl (bool): Enable crawling (start + info + pages). Default False.
        enable_map (bool): Enable website URL mapping. Default False.
        enable_batch (bool): Enable batch processing (create + info + items). Default False.
        all (bool): Enable all tools. Overrides individual flags when True. Default False.
        formats (Optional[List[str]]): Default formats for scrape (e.g. ["markdown", "html"]).
        country (Optional[str]): Default country code for scrape/batch.
        wait_before_scraping (Optional[int]): Default ms to wait before scraping.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        enable_scrape: bool = True,
        enable_answers: bool = True,
        enable_crawl: bool = False,
        enable_map: bool = False,
        enable_batch: bool = False,
        all: bool = False,
        formats: Optional[List[str]] = None,
        country: Optional[str] = None,
        wait_before_scraping: Optional[int] = None,
        **kwargs,
    ):
        self.api_key: Optional[str] = api_key or getenv("OLOSTEP_API_KEY")
        if not self.api_key:
            log_error("OLOSTEP_API_KEY not set. Please set the OLOSTEP_API_KEY environment variable.")

        self.formats: Optional[List[str]] = formats
        self.country: Optional[str] = country
        self.wait_before_scraping: Optional[int] = wait_before_scraping
        self.client: Olostep = Olostep(api_key=self.api_key)

        tools: List[Any] = []
        if all or enable_scrape:
            tools.append(self.scrape)
            tools.append(self.get_scrape)
        if all or enable_answers:
            tools.append(self.answer)
        if all or enable_crawl:
            tools.append(self.crawl)
            tools.append(self.get_crawl_info)
            tools.append(self.get_crawl_pages)
        if all or enable_map:
            tools.append(self.map_website)
        if all or enable_batch:
            tools.append(self.create_batch)
            tools.append(self.get_batch_info)
            tools.append(self.get_batch_items)

        super().__init__(name="olostep_tools", tools=tools, **kwargs)

    def scrape(
        self,
        url_to_scrape: str,
        formats: Optional[List[str]] = None,
        country: Optional[str] = None,
        wait_before_scraping: Optional[int] = None,
        parser: Optional[str] = None,
        remove_images: Optional[bool] = None,
    ) -> str:
        """Scrape a single URL and return its content.

        Args:
            url_to_scrape (str): The URL to scrape.
            formats (Optional[List[str]]): Output formats, e.g. ["markdown", "html", "text"].
            country (Optional[str]): Country code to route the request through (e.g. "US").
            wait_before_scraping (Optional[int]): Milliseconds to wait before scraping.
            parser (Optional[str]): Olostep parser ID (e.g. "@olostep/google-news").
            remove_images (Optional[bool]): Strip images from the scraped content.
        """
        params: Dict[str, Any] = {"url_to_scrape": url_to_scrape}
        formats = formats or self.formats
        if formats:
            params["formats"] = formats
        country = country or self.country
        if country:
            params["country"] = country
        wait = wait_before_scraping if wait_before_scraping is not None else self.wait_before_scraping
        if wait is not None:
            params["wait_before_scraping"] = wait
        if parser:
            params["parser"] = parser
        if remove_images is not None:
            params["remove_images"] = remove_images
        try:
            return _to_json(self.client.scrapes.create(**params))
        except Exception as e:
            error_msg = f"Error scraping with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def get_scrape(self, scrape_id: str) -> str:
        """Retrieve a previously created scrape by its ID.

        Args:
            scrape_id (str): The scrape ID returned by ``scrape``.
        """
        try:
            return _to_json(self.client.scrapes.get(scrape_id=scrape_id))
        except Exception as e:
            error_msg = f"Error getting scrape with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def answer(self, task: str, json_format: Optional[Dict[str, Any]] = None) -> str:
        """Run an AI answer task. Olostep searches the web and returns a structured answer.

        Args:
            task (str): A natural-language description of what to find or answer.
            json_format (Optional[Dict[str, Any]]): Optional JSON schema for structured output.
        """
        params: Dict[str, Any] = {"task": task}
        if json_format is not None:
            params["json_format"] = json_format
        try:
            return _to_json(self.client.answers.create(**params))
        except Exception as e:
            error_msg = f"Error answering with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def crawl(
        self,
        url: str,
        max_pages: Optional[int] = None,
        max_depth: Optional[int] = None,
        include_urls: Optional[List[str]] = None,
        exclude_urls: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        top_n: Optional[int] = None,
        include_subdomain: Optional[bool] = None,
        include_external: Optional[bool] = None,
    ) -> str:
        """Start crawling a website starting from ``url``.

        Args:
            url (str): URL to start crawling from.
            max_pages (Optional[int]): Max number of pages to crawl.
            max_depth (Optional[int]): Maximum link depth from the start URL.
            include_urls (Optional[List[str]]): Glob patterns of URLs to include.
            exclude_urls (Optional[List[str]]): Glob patterns of URLs to exclude.
            search_query (Optional[str]): Only process pages matching this query.
            top_n (Optional[int]): Max number of results.
            include_subdomain (Optional[bool]): Include subdomain links.
            include_external (Optional[bool]): Include external links.
        """
        params: Dict[str, Any] = {"url": url}
        if max_pages is not None:
            params["max_pages"] = max_pages
        if max_depth is not None:
            params["max_depth"] = max_depth
        if include_urls:
            params["include_urls"] = include_urls
        if exclude_urls:
            params["exclude_urls"] = exclude_urls
        if search_query:
            params["search_query"] = search_query
        if top_n is not None:
            params["top_n"] = top_n
        if include_subdomain is not None:
            params["include_subdomain"] = include_subdomain
        if include_external is not None:
            params["include_external"] = include_external
        try:
            return _to_json(self.client.crawls.create(**params))
        except Exception as e:
            error_msg = f"Error starting crawl with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def get_crawl_info(self, crawl_id: str) -> str:
        """Get status and progress for a crawl.

        Args:
            crawl_id (str): The crawl ID returned by ``crawl``.
        """
        try:
            return _to_json(self.client.crawls.info(crawl_id=crawl_id))
        except Exception as e:
            error_msg = f"Error retrieving crawl with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def get_crawl_pages(
        self,
        crawl_id: str,
        search_query: Optional[str] = None,
        wait_for_completion: bool = True,
        max_pages: Optional[int] = None,
    ) -> str:
        """List pages discovered by a crawl.

        Args:
            crawl_id (str): The crawl ID.
            search_query (Optional[str]): Only return pages matching this query.
            wait_for_completion (bool): Wait for the crawl to finish before listing. Default True.
            max_pages (Optional[int]): Cap the number of pages returned. Default: all.
        """
        params: Dict[str, Any] = {"crawl_id": crawl_id, "wait_for_completion": wait_for_completion}
        if search_query:
            params["search_query"] = search_query
        try:
            iterator = self.client.crawls.pages(**params)
            pages: List[Any] = []
            for i, page in enumerate(iterator):
                if max_pages is not None and i >= max_pages:
                    break
                if hasattr(page, "model_dump"):
                    pages.append(page.model_dump())
                elif hasattr(page, "to_dict"):
                    pages.append(page.to_dict())
                else:
                    pages.append(page)
            return json.dumps({"pages": pages}, cls=CustomJSONEncoder)
        except Exception as e:
            error_msg = f"Error listing crawl pages with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def map_website(
        self,
        url: str,
        search_query: Optional[str] = None,
        top_n: Optional[int] = None,
        include_urls: Optional[List[str]] = None,
        exclude_urls: Optional[List[str]] = None,
        include_subdomain: Optional[bool] = None,
    ) -> str:
        """Return all URLs found on a website.

        Args:
            url (str): The website to map.
            search_query (Optional[str]): Filter links by this query.
            top_n (Optional[int]): Max number of links.
            include_urls (Optional[List[str]]): Glob patterns of URLs to include.
            exclude_urls (Optional[List[str]]): Glob patterns of URLs to exclude.
            include_subdomain (Optional[bool]): Include subdomain links.
        """
        params: Dict[str, Any] = {"url": url}
        if search_query:
            params["search_query"] = search_query
        if top_n is not None:
            params["top_n"] = top_n
        if include_urls:
            params["include_urls"] = include_urls
        if exclude_urls:
            params["exclude_urls"] = exclude_urls
        if include_subdomain is not None:
            params["include_subdomain"] = include_subdomain
        try:
            return _to_json(self.client.maps.create(**params))
        except Exception as e:
            error_msg = f"Error mapping with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def create_batch(
        self,
        urls: Union[str, List[str], List[Dict[str, str]]],
        country: Optional[str] = None,
        parser: Optional[str] = None,
    ) -> str:
        """Create a batch scraping job for multiple URLs.

        Args:
            urls: A single URL, a list of URLs, or a list of {"url": ..., "custom_id": ...} dicts.
            country (Optional[str]): Country code for geolocation.
            parser (Optional[str]): Olostep parser ID (e.g. "@olostep/google-news").
        """
        params: Dict[str, Any] = {"urls": urls}
        country = country or self.country
        if country:
            params["country"] = country
        if parser:
            params["parser"] = parser
        try:
            return _to_json(self.client.batches.create(**params))
        except Exception as e:
            error_msg = f"Error creating batch with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def get_batch_info(self, batch_id: str) -> str:
        """Get status and progress for a batch.

        Args:
            batch_id (str): The batch ID returned by ``create_batch``.
        """
        try:
            return _to_json(self.client.batches.info(batch_id=batch_id))
        except Exception as e:
            error_msg = f"Error retrieving batch with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})

    def get_batch_items(
        self,
        batch_id: str,
        status: Optional[str] = None,
        wait_for_completion: bool = True,
        max_items: Optional[int] = None,
    ) -> str:
        """List items in a batch.

        Args:
            batch_id (str): The batch ID.
            status (Optional[str]): Filter by item status (e.g. "completed", "failed").
            wait_for_completion (bool): Wait for the batch to finish before listing. Default True.
            max_items (Optional[int]): Cap the number of items returned. Default: all.
        """
        params: Dict[str, Any] = {"batch_id": batch_id, "wait_for_completion": wait_for_completion}
        if status:
            params["status"] = status
        try:
            iterator = self.client.batches.items(**params)
            items: List[Any] = []
            for i, item in enumerate(iterator):
                if max_items is not None and i >= max_items:
                    break
                if hasattr(item, "model_dump"):
                    items.append(item.model_dump())
                elif hasattr(item, "to_dict"):
                    items.append(item.to_dict())
                else:
                    items.append(item)
            return json.dumps({"items": items}, cls=CustomJSONEncoder)
        except Exception as e:
            error_msg = f"Error listing batch items with Olostep: {str(e)}"
            log_error(error_msg)
            return json.dumps({"error": error_msg})
