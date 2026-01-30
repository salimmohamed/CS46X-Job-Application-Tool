// header for the extension popup
import './PopupHeader.css';

interface PopupHeaderProps {
  userName?: string;
  onSettingsClick?: () => void;
}

export function PopupHeader({ onSettingsClick }: PopupHeaderProps) {
  return (
    <header className="popup-header">
      <div className="popup-header-left" />
      <button
        className="popup-header-settings"
        onClick={onSettingsClick}
        aria-label="Settings"
      >
        Settings
      </button>
    </header>
  );
}
