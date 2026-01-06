import { useState } from 'react';
import { useTheme, THEME_CONFIG } from '../contexts/ThemeContext';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Card } from './ui/card';
import { Check, Palette } from 'lucide-react';

interface ThemeSelectorProps {
  trigger?: React.ReactNode;
}

export function ThemeSelector({ trigger }: ThemeSelectorProps) {
  const { theme: currentTheme, setTheme } = useTheme();
  const [open, setOpen] = useState(false);

  const handleThemeSelect = (theme: 'ocean' | 'cyberpunk' | 'minimal') => {
    setTheme(theme);
    setTimeout(() => setOpen(false), 300);
  };

  return (
    <>
      {trigger ? (
        <div onClick={() => setOpen(true)}>{trigger}</div>
      ) : (
        <Button
          variant="ghost"
          onClick={() => setOpen(true)}
          className="w-full justify-start gap-2"
        >
          <Palette className="w-4 h-4" />
          <span>Theme</span>
        </Button>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-[600px] bg-card border-border">
          <DialogHeader>
            <DialogTitle className="text-foreground flex items-center gap-2">
              <Palette className="w-5 h-5 text-primary" />
              Choose Your Theme
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Select a visual theme that matches your style
            </DialogDescription>
          </DialogHeader>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 py-4">
            {(Object.keys(THEME_CONFIG) as Array<keyof typeof THEME_CONFIG>).map((themeKey) => {
              const config = THEME_CONFIG[themeKey];
              const isSelected = currentTheme === themeKey;

              return (
                <Card
                  key={themeKey}
                  className={`
                    relative cursor-pointer transition-all duration-200 overflow-hidden
                    ${isSelected ? 'ring-2 ring-primary shadow-lg' : 'hover:scale-105 hover:shadow-md'}
                  `}
                  onClick={() => handleThemeSelect(themeKey)}
                >
                  {/* Preview */}
                  <div
                    className="h-32 relative"
                    style={{ background: config.preview.bg }}
                  >
                    {/* Preview elements */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-center space-y-2">
                        <div 
                          className="text-4xl mb-2"
                          style={{ 
                            color: config.preview.accent,
                            filter: themeKey === 'cyberpunk' ? 'drop-shadow(0 0 10px currentColor)' : 'none'
                          }}
                        >
                          {config.icon}
                        </div>
                        <div className="space-y-1">
                          <div
                            className="h-2 w-16 mx-auto rounded"
                            style={{ backgroundColor: config.preview.accent }}
                          />
                          <div
                            className="h-1 w-12 mx-auto rounded opacity-50"
                            style={{ backgroundColor: config.preview.text }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Selected indicator */}
                    {isSelected && (
                      <div className="absolute top-2 right-2">
                        <div className="bg-primary rounded-full p-1">
                          <Check className="w-4 h-4 text-primary-foreground" />
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="p-4 bg-card">
                    <h3 className="font-semibold text-card-foreground mb-1">
                      {config.name}
                    </h3>
                    <p className="text-xs text-muted-foreground">
                      {config.description}
                    </p>
                  </div>
                </Card>
              );
            })}
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-border">
            <Button variant="outline" onClick={() => setOpen(false)}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
