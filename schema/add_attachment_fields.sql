-- Add attachment fields to processed_emails table
-- Fixed version for FinMatcher

DO $$ 
BEGIN
    -- Add attachment_file if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='processed_emails' AND column_name='attachment_file') THEN
        ALTER TABLE processed_emails ADD COLUMN attachment_file BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added attachment_file column';
    ELSE
        RAISE NOTICE 'attachment_file column already exists';
    END IF;
    
    -- Add attachment_file_path if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='processed_emails' AND column_name='attachment_file_path') THEN
        ALTER TABLE processed_emails ADD COLUMN attachment_file_path TEXT;
        RAISE NOTICE 'Added attachment_file_path column';
    ELSE
        RAISE NOTICE 'attachment_file_path column already exists';
    END IF;
    
    -- Add attachment_image_path if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='processed_emails' AND column_name='attachment_image_path') THEN
        ALTER TABLE processed_emails ADD COLUMN attachment_image_path TEXT;
        RAISE NOTICE 'Added attachment_image_path column';
    ELSE
        RAISE NOTICE 'attachment_image_path column already exists';
    END IF;
END $$;

-- Create indexes for attachment fields
CREATE INDEX IF NOT EXISTS idx_emails_attachment_file 
ON processed_emails(attachment_file) 
WHERE attachment_file = TRUE;

CREATE INDEX IF NOT EXISTS idx_emails_attachment_file_path 
ON processed_emails(attachment_file_path) 
WHERE attachment_file_path IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_emails_attachment_image 
ON processed_emails(attachment_image_path) 
WHERE attachment_image_path IS NOT NULL;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Attachment fields added successfully to processed_emails table!';
END $$;
