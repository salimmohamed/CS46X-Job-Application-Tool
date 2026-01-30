// tab navigation for the extension popup
import './PopupFooter.css';

type TabType = 'profile' | 'matches' | 'saved';

interface PopupFooterProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export function PopupFooter({ activeTab, onTabChange }: PopupFooterProps) {
  return (
    <footer className="popup-footer">
      <button
        className={`popup-footer-tab ${activeTab === 'profile' ? 'active' : ''}`}
        onClick={() => onTabChange('profile')}
      >
        Profile
      </button>
      <button
        className={`popup-footer-tab ${activeTab === 'matches' ? 'active' : ''}`}
        onClick={() => onTabChange('matches')}
      >
        Matches
      </button>
      <button
        className={`popup-footer-tab ${activeTab === 'saved' ? 'active' : ''}`}
        onClick={() => onTabChange('saved')}
      >
        Saved
      </button>
    </footer>
  );
}
