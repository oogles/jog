import sys
from io import TextIOBase

#
# This module is heavily based on Django, adapted from functionality found in
# ``django.core.management.base``, ``django.core.management.color``, and
# ``django.utils.termcolors``.
#

COLOR_NAMES = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
FOREGROUND = {COLOR_NAMES[x]: '3%s' % x for x in range(8)}
BACKGROUND = {COLOR_NAMES[x]: '4%s' % x for x in range(8)}

OPTIONS = {'bold': '1', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}
RESET = '\x1b[0m'


def style(text='', fg=None, bg=None, options=(), reset=True):
    """
    Return ``text``, enclosed in ANSI graphics codes, as dictated by
    ``fg``, ``bg``, and ``options``. If ``reset`` is ``True``, the returned
    text will be terminated by the RESET code. Return just RESET code if no
    parameters are given.
    
    Valid colors:
        'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white'
    
    Valid options:
        'bold', 'underscore', 'blink', 'reverse', 'conceal'
    
    Examples:
        style('hello', fg='red', bg='blue', opts=('blink', ))
        style()
        style('goodbye', opts=('underscore', ))
        print(style('first line', fg='red', reset=False))
        print('this should be red too')
        print(style('and so should this'))
        print('this should not be red')
    """
    
    if reset:
        text = f'{text}{RESET}'
    
    code_list = []
    
    if fg:
        code_list.append(FOREGROUND[fg])
    
    if bg:
        code_list.append(BACKGROUND[bg])
    
    for o in options:
        code_list.append(OPTIONS[o])
    
    code_list = ';'.join(code_list)
    return f'\x1b[{code_list}m{text}'


def make_style(**kwargs):
    """
    Return a function with default parameters for style().
    
    Example:
        bold_red = make_style(opts=('bold',), fg='red')
        print(bold_red('hello'))
        KEYWORD = make_style(fg='yellow')
        COMMENT = make_style(fg='blue', opts=('bold',))
    """
    
    return lambda text: style(text, **kwargs)


class Styler:
    
    PALETTE = {
        'success': {'fg': 'green', 'options': ('bold', )},
        'error': {'fg': 'red', 'options': ('bold', )},
        'warning': {'fg': 'yellow', 'options': ('bold', )},
        'info': {'options': ('bold', )},
        'debug': {'fg': 'magenta', 'options': ('bold', )},
        'heading': {'fg': 'cyan', 'options': ('bold', )},
        'label': {'options': ('bold', )},
    }
    
    def __init__(self, no_color=False):
        
        self.no_color = no_color
        
        if no_color:
            for role in self.PALETTE:
                setattr(self, role, lambda text: text)
        else:
            for role, fmt in self.PALETTE.items():
                setattr(self, role, make_style(**fmt))
    
    def apply(self, text, *args, **kwargs):
        
        if self.no_color:
            return text
        
        return style(text, *args, **kwargs)


class OutputWrapper(TextIOBase):
    """
    Simple wrapper around ``stdout``/``stderr`` to normalise some behaviours.
    """
    
    def __init__(self, out, ending='\n', default_style=None, no_color=False):
        
        self._out = out
        self.ending = ending
        
        no_color = no_color or not self.supports_color()
        self.styler = Styler(no_color)
        self.default_style = default_style
    
    def __getattr__(self, name):
        
        return getattr(self._out, name)
    
    def supports_color(self):
        """
        Return True if the output stream supports color, and False otherwise.
        """
        
        plat = sys.platform
        supported_platform = plat != 'Pocket PC' and (plat != 'win32' or 'ANSICON' in os.environ)
        is_a_tty = hasattr(self._out, 'isatty') and self._out.isatty()
        
        return supported_platform and is_a_tty
    
    def write(self, msg, style=None, use_ending=True):
        
        if use_ending:
            msg += self.ending
        
        style = style or self.default_style
        if style:
            msg = getattr(self.styler, style)(msg)
        
        self._out.write(msg)
