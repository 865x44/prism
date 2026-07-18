import subprocess
from unittest import mock
import pytest
from prism.slice.provider import _call_opencode, TransportError

def test_opencode_privacy():
    """Test that the prompt is passed via stdin, not argv."""
    prompt_text = "SECRET_PROMPT_DO_NOT_LEAK"
    
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(
            returncode=0,
            stdout="fake response",
            stderr=""
        )
        
        result = _call_opencode(prompt_text, "fake-model")
        
        assert result == "fake response"
        
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        
        # Check argv doesn't contain the prompt
        assert prompt_text not in args[0]
        
        # Check input contains the prompt
        assert kwargs.get("input") == prompt_text
