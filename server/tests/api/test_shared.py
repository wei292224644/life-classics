"""测试通用分页模型 Paginated[T]。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.shared import Paginated


def test_paginated_basic_fields():
    result = Paginated(items=[1, 2], total=10, offset=0, limit=2, has_more=True)
    assert result.items == [1, 2]
    assert result.total == 10
    assert result.offset == 0
    assert result.limit == 2
    assert result.has_more is True


def test_paginated_has_more_false():
    result = Paginated(items=[], total=5, offset=4, limit=2, has_more=False)
    assert result.has_more is False


def test_paginated_empty_items():
    result = Paginated(items=[], total=0, offset=0, limit=20, has_more=False)
    assert result.total == 0
    assert result.items == []
