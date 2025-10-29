# -*- coding: utf-8 -*-
"""Simple logger for the application"""
import logging

# Configure basic logger
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)

logger = logging.getLogger(__name__)
