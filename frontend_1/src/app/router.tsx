import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';

// Features & Pages
import { DashboardPage } from '../features/dashboard/DashboardPage';
import { BusinessesPage } from '../features/businesses/BusinessesPage';
import { BusinessDetailPage } from '../features/businesses/BusinessDetailPage';
import { CallsPage } from '../features/calls/CallsPage';
import { ActiveCallsPage } from '../features/calls/ActiveCallsPage';
import { QueuePage } from '../features/calls/QueuePage';
import { AgentsPage } from '../features/agents/AgentsPage';
import { AgentWorkspacePage } from '../features/agents/AgentWorkspacePage';
import { QuestionnairesPage } from '../features/questionnaires/QuestionnairesPage';
import { QuestionnaireEditorPage } from '../features/questionnaires/QuestionnaireEditorPage';
import { CampaignsPage } from '../features/campaigns/CampaignsPage';
import { ContactsPage } from '../features/contacts/ContactsPage';
import { LeadsPage } from '../features/leads/LeadsPage';
import { FollowupsPage } from '../features/followups/FollowupsPage';
import { ReportsPage } from '../features/reports/ReportsPage';
import { InvoicesPage } from '../features/invoices/InvoicesPage';
import { ModelConfigPage } from '../features/models/ModelConfigPage';
import { ModelLabPage } from '../features/model_lab/ModelLabPage';
import { HealthPage } from '../features/health/HealthPage';
import { SettingsPage } from '../features/settings/SettingsPage';
import { LookPage } from '../features/modern/LookPage';
import { ModernDashboard } from '../features/modern/ModernDashboard';
import { ModernLeads } from '../features/modern/ModernLeads';
import { ModernCalls } from '../features/modern/ModernCalls';
import { ModernAgents } from '../features/modern/ModernAgents';
import { ModernBusinesses } from '../features/modern/ModernBusinesses';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <LookPage classic={<DashboardPage />} modern={<ModernDashboard />} /> },
      { path: 'businesses', element: <LookPage classic={<BusinessesPage />} modern={<ModernBusinesses />} /> },
      { path: 'businesses/:id', element: <BusinessDetailPage /> },
      { path: 'calls', element: <LookPage classic={<CallsPage />} modern={<ModernCalls />} /> },
      { path: 'active-calls', element: <ActiveCallsPage /> },
      { path: 'queue', element: <QueuePage /> },
      { path: 'model-lab', element: <ModelLabPage /> },
      { path: 'agents', element: <LookPage classic={<AgentsPage />} modern={<ModernAgents />} /> },
      { path: 'agents/:id', element: <AgentWorkspacePage /> },
      { path: 'questionnaires', element: <QuestionnairesPage /> },
      { path: 'questionnaires/:id', element: <QuestionnaireEditorPage /> },
      { path: 'campaigns', element: <CampaignsPage /> },
      { path: 'contacts', element: <ContactsPage /> },
      { path: 'leads', element: <LookPage classic={<LeadsPage />} modern={<ModernLeads />} /> },
      { path: 'followups', element: <FollowupsPage /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'invoices', element: <InvoicesPage /> },
      { path: 'settings/models', element: <ModelConfigPage /> },
      { path: 'settings/health', element: <HealthPage /> },
      { path: 'settings/telephony', element: <SettingsPage initialTab="telephony" /> },
      { path: 'settings/transcript', element: <SettingsPage initialTab="transcript" /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]);
